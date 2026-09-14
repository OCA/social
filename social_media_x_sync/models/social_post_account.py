# Copyright 2026 Binhex <https://www.binhex.cloud>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import logging
from collections import Counter

from tweepy.errors import TooManyRequests

from odoo import _, fields, models

from ..social_x_sync_utils import _COMMENTS_MAX_PAGES_X, _SEARCH_MAX_RESULTS_X

_logger = logging.getLogger(__name__)


class SocialPostAccount(models.Model):
    """Publication, comments and statistics of a post on an X account."""

    _inherit = "social.post.account"

    def _x_comment_parent_ref(self, tweet, comment_refs):
        """Return the comment a tweet of the thread answers.

        The search that reads the comments asks for the conversation, so the
        replies of a reply arrive along with the comments of the post. What
        tells them apart is already in the payload: the ``replied_to``
        reference of a comment is the post, and that of a reply is another
        tweet of the list.

        The references are those of everything the walk of the pages brought,
        never those of one page: a tweet answering a comment left on a page
        that was never read hangs from the publication, which is not where it
        was written.

        :param tweet: one tweet as X answered it.
        :param comment_refs: the references of every tweet of the thread.
        :return: the reference of the answered comment, ``False`` when the
            tweet hangs from the publication.
        :rtype: str or bool
        """
        for referenced in getattr(tweet, "referenced_tweets", None) or []:
            if referenced.type != "replied_to":
                continue
            parent_ref = str(referenced.id)
            return parent_ref if parent_ref in comment_refs else False
        return False

    def _x_comments_quota_answer(self):
        """Answer of a read the quota of X did not let happen.

        The details —limit, remaining and when to retry— are already on their
        way to the user from :meth:`_get_message_many_requests`, so what
        travels here is only what the client needs to tell an unread thread
        from a publication with no comments.

        :rtype: dict
        """
        return {
            "success": False,
            "message": _(
                "The comments could not be read from X. The account may have "
                "reached the limit of requests of its plan."
            ),
        }

    def _x_comment_quota_answer(self):
        """Answer of a reply the quota of X did not let happen.

        The details —limit, remaining and when to retry— are already on their
        way to the user from :meth:`_get_message_many_requests`, so what
        travels here is only what the client needs to tell a reply X never
        received from one it published.

        :rtype: dict
        """
        return {
            "success": False,
            "message": _(
                "The comment could not be published on X. The account may "
                "have reached the limit of requests of its plan."
            ),
            "post_deleted": False,
        }

    def _x_read_conversation(self, client_api, query):
        """Walk the pages of a conversation and return what they carried.

        The recent search endpoint answers one page at a time and names the
        next one in ``meta``. Without that walk the thread Odoo reads is the
        first page and nothing else, so a reply whose comment stayed on a
        later page is drawn hanging from the publication instead of from it.

        The walk stops at :data:`_COMMENTS_MAX_PAGES_X`, which is what keeps
        one dialog from spending the quota of the whole database.

        The quota is what else cuts it short. Reaching it on a later page
        keeps the pages already read, because throwing them away pays their
        cost for nothing; on the first one there is nothing to keep, so the
        error travels up and the caller answers what it always answered.

        :param client_api: the client of X the account speaks through.
        :param query: the search query naming the conversation.
        :return: the tweets read, the authors and the media by their key, and
            whether the conversation was left unfinished.
        :rtype: tuple(list, dict, dict, bool)
        :raise TooManyRequests: when the quota stopped the very first page.
        """
        tweets = []
        users = {}
        media_urls = {}
        next_token = None
        for _page in range(_COMMENTS_MAX_PAGES_X):
            try:
                response = client_api.search_recent_tweets(
                    query=query,
                    tweet_fields=[
                        "id",
                        "text",
                        "author_id",
                        "created_at",
                        "conversation_id",
                        "attachments",
                        "in_reply_to_user_id",
                    ],
                    expansions=[
                        "author_id",
                        "in_reply_to_user_id",
                        "referenced_tweets.id",
                        "attachments.media_keys",
                        "referenced_tweets.id.author_id",
                    ],
                    user_fields="id,name,username,profile_image_url",
                    media_fields=["media_key", "type", "url"],
                    max_results=_SEARCH_MAX_RESULTS_X,
                    next_token=next_token,
                )
            except TooManyRequests as exManyRequest:
                if not tweets:
                    raise
                self.account_id._get_message_many_requests(
                    exManyRequest, endpoint="get_comments"
                )
                return tweets, users, media_urls, True
            tweets.extend(response.data or [])
            includes = getattr(response, "includes", None) or {}
            # Merged by key instead of concatenated: the same author or the
            # same media comes back on every page they appear in.
            for user in includes.get("users") or []:
                users[str(user.id)] = user
            for media in includes.get("media") or []:
                if media.url:
                    media_urls[media.media_key] = media.url
            # Read defensively because a page without ``meta`` is a page
            # without a next one, and anything that is not a mapping says
            # nothing about where the conversation continues.
            meta = getattr(response, "meta", None) or {}
            next_token = meta.get("next_token") if isinstance(meta, dict) else None
            if not next_token:
                break
        return tweets, users, media_urls, bool(next_token)

    def get_comments(self):
        """Read the replies to this post.

        :return: ``success`` and the list of comments, or the error message.
        :rtype: dict
        """
        data = super().get_comments()
        comments = []
        if "x" == self.account_id.media_type:
            try:
                result = self.account_id._valid_time_request(endpoint="get_comments")
                if not result:
                    return self._x_comments_quota_answer()
                client_api = self.account_id.get_client_api(
                    bearer_token=self.account_id.sudo().x_access_token_oauth2
                )
                query = (
                    f"conversation_id:{self.remote_ref} "
                    f"is:reply -is:retweet -is:quote"
                )
                (
                    tweets,
                    users,
                    media_urls,
                    truncated,
                ) = self._x_read_conversation(client_api, query)
                if tweets:
                    # Both are read from everything the walk brought, so a
                    # reply of one page whose comment came on another still
                    # finds it.
                    comment_refs = {str(tweet.id) for tweet in tweets}
                    for comment in tweets:
                        author = users.get(str(comment.author_id))
                        media_keys = (getattr(comment, "attachments", {}) or {}).get(
                            "media_keys", []
                        )
                        comments.append(
                            {
                                "id": str(comment.id),
                                # On X a comment is a tweet, so what names
                                # it is its own identifier, and that is
                                # what a reply is published against.
                                "remote_ref": str(comment.id),
                                "parent_ref": self._x_comment_parent_ref(
                                    comment, comment_refs
                                ),
                                "text": comment.text,
                                "actor": author.name,
                                # X stamps a tweet with a moment carrying its
                                # offset, and what the client draws is how
                                # long ago it was, the same sentence every
                                # social media answers with.
                                "published_time": self._format_published_time(
                                    comment.created_at
                                ),
                                "author_image": author.profile_image_url
                                if author.profile_image_url
                                else None,
                                "images_url": [
                                    media_urls[media_key]
                                    for media_key in media_keys
                                    if media_key in media_urls
                                ],
                            }
                        )
                    if truncated:
                        # The replies of a comment may be on the page that
                        # was never read, so there is no total to state.
                        # ``None`` is what the contract reserves for it, and
                        # the client offers to unfold the replies instead of
                        # hiding them behind a zero it cannot back.
                        for comment in comments:
                            comment["reply_count"] = None
                    else:
                        # The walk reached the end, so how many replies each
                        # comment has is counted here and never asked to X
                        # again.
                        reply_counts = Counter(
                            comment["parent_ref"]
                            for comment in comments
                            if comment["parent_ref"]
                        )
                        for comment in comments:
                            comment["reply_count"] = reply_counts.get(
                                comment["remote_ref"], 0
                            )

            except TooManyRequests as exManyRequest:
                self.account_id._get_message_many_requests(
                    exManyRequest, endpoint="get_comments"
                )
                return self._x_comments_quota_answer()
            except Exception as e:  # noqa: BLE001 - tweepy may fail in any way
                return_message = _("Error Get Comments for Tweet: %(error)s", error=e)
                _logger.exception(
                    "Error getting the comments of tweet %s", self.remote_ref
                )
                return {
                    "success": False,
                    "message": return_message,
                }
            return {
                "success": True,
                "data": data.get("data", []) + comments,
            }
        # Answered untouched, ``success`` included: what another social media
        # said about its own comments is not this connector's to rewrite, and
        # the message explaining a failure of its own would go with it.
        return data

    def create_x_comment(self, post_data):
        """Publish a reply to this post, with its attachments if any.

        :rtype: dict
        """
        if "x" == self.account_id.media_type:
            try:
                result = self.account_id._valid_time_request(endpoint="create_comment")
                if not result:
                    return self._x_comment_quota_answer()
                client_api = self.account_id.get_client_api()
                # A reply to a comment answers that tweet instead of the
                # post: on X both are tweets and the only difference is
                # which one is being replied to.
                parent_ref = post_data.get("social_parent_ref")
                target = parent_ref or self.remote_ref
                attachment_ids = self.env["ir.attachment"]
                if post_data.get("attachment_ids", False) and post_data.get(
                    "body", False
                ):
                    attachment_ids = self.env["ir.attachment"].browse(
                        post_data.get("attachment_ids", [])
                    )
                    # The images of a comment are not stored on the
                    # publication, so only what X calls them is needed.
                    media_refs = self.account_id._prepare_medias_for_tweet(
                        image_ids=attachment_ids
                    )
                    response = client_api.create_tweet(
                        text=post_data.get("body", ""),
                        in_reply_to_tweet_id=target,
                        media_ids=list(media_refs.values()),
                    )
                else:
                    response = client_api.create_tweet(
                        text=post_data.get("body", ""),
                        in_reply_to_tweet_id=target,
                    )
            except TooManyRequests as exManyRequest:
                self.account_id._get_message_many_requests(
                    exManyRequest, endpoint="create_comment"
                )
                return self._x_comment_quota_answer()
            except Exception as exp:  # noqa: BLE001 - tweepy may fail in any way
                # X refuses a reply to a post that is gone in more than one
                # shape — a ``400`` and a ``403`` both mean it — so the post
                # itself is asked about instead of reading the error.
                post_deleted = self._remote_post_gone_on_action()
                return_message = (
                    _("The post does not exist or has been deleted.")
                    if post_deleted
                    else _("Error Comment Tweet: %(error)s", error=exp)
                )
                _logger.exception("Error replying to tweet %s", self.remote_ref)
                return {
                    "success": False,
                    "message": return_message,
                    "post_deleted": post_deleted,
                }
            return {
                "success": True,
                "post_deleted": False,
                **self._x_created_comment(response, parent_ref, attachment_ids),
            }
        return {
            "success": True,
            "post_deleted": False,
        }

    def _x_created_comment(self, response, parent_ref, attachments):
        """Shape the tweet X answers as the comment the client draws.

        X answers the creation with the identifier and the text of the tweet,
        and everything else is known here without asking: the comment was
        written by this account, at this moment, with the images that went up
        with it. A creation that answers no identifier answers nothing, and
        the client rereads the thread instead.

        :param response: the answer of tweepy to the creation.
        :param parent_ref: the comment the tweet answers, ``False`` when it
            hangs from the publication.
        :param attachments: the images published with the comment.
        :return: ``{"comment": …}``, or empty when it cannot be shaped.
        :rtype: dict
        """
        data = getattr(response, "data", None) or {}
        remote_ref = str(data.get("id") or "")
        if not remote_ref:
            return {}
        return {
            "comment": {
                "id": remote_ref,
                "remote_ref": remote_ref,
                "parent_ref": parent_ref or False,
                # What X stored, which is not always what was sent: the text
                # comes back shortened when it carries a link.
                "text": data.get("text") or "",
                "actor": self.account_id.name,
                # The reply was written just now, and the client draws how
                # long ago that is like it does for every other comment.
                "published_time": self._format_published_time(fields.Datetime.now()),
                "author_image": None,
                "images_url": [
                    f"/web/image/{attachment.id}" for attachment in attachments
                ],
                "reply_count": 0,
                "liked": False,
            }
        }

    def create_comment(self, post_data, context=None):
        if "x" == self.account_id.media_type:
            return self.create_x_comment(post_data)
        else:
            return super().create_comment(post_data, context)

    def _get_assets_save_x(self, media_keys, media_map):
        """Download the media of a tweet that are not stored yet.

        :return: The attachments created and the media key of each one, keyed
            by its identifier. Both go into the same write, so that a
            downloaded media is never stored without the reference telling it
            apart from one attached in Odoo.
        :rtype: tuple
        """
        medias_exist = self._get_medias_account(media_keys)
        url_by_ref = {}
        for media in media_keys:
            if media in medias_exist:
                continue
            media_data = media_map.get(media)
            url_by_ref[media] = media_data and media_data[1]
        return self._store_remote_medias(url_by_ref)
