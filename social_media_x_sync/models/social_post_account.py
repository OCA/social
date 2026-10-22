# Copyright 2026 Binhex <https://www.binhex.cloud>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import logging
from collections import Counter

from tweepy.errors import Forbidden, NotFound, TooManyRequests, Unauthorized

from odoo import _, api, fields, models

from odoo.addons.social_media_x.social_x_utils import _URL_PRICING_X

from ..social_x_sync_utils import (
    _COMMENTS_MAX_PAGES_X,
    _SEARCH_MAX_RESULTS_X,
    _SKIP_LIKES_CONTEXT_X,
    _VIDEO_CONTENT_TYPE_X,
    _VIDEO_MEDIA_TYPES_X,
    _strip_media_links_x,
)

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

    @api.model
    def _x_comment_media_url(self, media):
        """Return the image the dialog draws for a media of a comment.

        A photo is drawn from its ``url``. A video or an animated GIF has
        none, so its cover, ``preview_image_url``, is drawn instead: the
        dialog shows images only, and the video is watched on X.

        :param media: one media as X answered it.
        :return: the address of the image, or ``None`` when X gave none.
        :rtype: str
        """
        if media.type in _VIDEO_MEDIA_TYPES_X:
            return media.preview_image_url
        return media.url

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
                        "entities",
                    ],
                    expansions=[
                        "author_id",
                        "in_reply_to_user_id",
                        "referenced_tweets.id",
                        "attachments.media_keys",
                        "referenced_tweets.id.author_id",
                    ],
                    user_fields="id,name,username,profile_image_url",
                    media_fields=["media_key", "type", "url", "preview_image_url"],
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
                media_url = self._x_comment_media_url(media)
                if media_url:
                    media_urls[media.media_key] = media_url
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
                    # The likes are read when the dialog opens. A refresh
                    # asks without them, and the client keeps those it
                    # already holds for the comments it already draws.
                    liked_refs = None
                    if not self.env.context.get(_SKIP_LIKES_CONTEXT_X):
                        liked_refs = self.account_id._x_liked_refs()
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
                                "text": _strip_media_links_x(
                                    comment.text, comment.entities
                                ),
                                "actor": author.name,
                                # Who wrote it, which is what tells a comment
                                # of the account, the only one X lets it
                                # delete.
                                "author_ref": str(comment.author_id),
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
                                "liked": str(comment.id) in (liked_refs or ()),
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
                "author_ref": self.account_id.remote_ref,
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

    def _x_refused_credentials_message(self, error):
        """Flag the account whose token X refused and explain it.

        :param error: the ``Unauthorized`` raised by tweepy.
        :return: the message the client shows.
        :rtype: str
        """
        self.account_id._flag_credentials_expired(str(error))
        return _(
            "X refused the credentials of %(account)s. Update the account "
            "to authorize it again.",
            account=self.account_id.display_name,
        )

    def _x_forbidden_message(self, error):
        """Explain a request X refused, telling apart the App that cannot spend.

        The message is drawn as plain text by the client, so the link to the
        pricing page travels as its address.

        :param error: the ``Forbidden`` raised by tweepy.
        :return: the message the client shows.
        :rtype: str
        """
        return str(self.account_id._x_error_message(error, pricing_link=_URL_PRICING_X))

    def _x_react(self, tweet_ref, like):
        """Give or withdraw the like of the account on a tweet of X.

        A publication and a comment are both tweets on X, so the same call
        serves the four reaction actions. It speaks with the user context of
        the account, the one that publishes and deletes: tweepy reads whom
        the like belongs to from the OAuth1 token, without asking X, so the
        actor is always the account and never something the client names.

        :param tweet_ref: identifier of the tweet on X.
        :param like: ``True`` to give the like, ``False`` to withdraw it.
        :return: what X holds once the call is over, or ``None`` when the
            window of the quota is still open and nothing was asked.
        :rtype: bool or None
        :raise ValueError: when X answers without saying whether the like is
            there, which is how it reports a tweet that no longer exists.
        """
        if not self.account_id._valid_time_request(endpoint="like"):
            return None
        client_api = self.account_id.get_client_api()
        if like:
            response = client_api.like(tweet_ref)
        else:
            response = client_api.unlike(tweet_ref)
        data = getattr(response, "data", None) or {}
        if "liked" not in data:
            raise ValueError(getattr(response, "errors", None) or data)
        return bool(data["liked"])

    def _x_reaction_answer(self, tweet_ref, like, liked):
        """Send a reaction to X and answer what the client expects.

        Nothing raises from here: the client waits for a dict, so a token X
        refuses flags the account and is answered as a failure, the same way
        :meth:`create_x_comment` answers its own.

        :param tweet_ref: identifier of the tweet on X.
        :param like: ``True`` to give the like, ``False`` to withdraw it.
        :param liked: what to answer in ``liked`` when X does not say.
        :return: ``success``, ``message``, ``post_deleted`` and ``liked``.
        :rtype: dict
        """
        answer = {
            "success": False,
            "message": "",
            "post_deleted": False,
            "liked": liked,
        }
        quota_message = _(
            "The recommendation could not be sent to X. The account may have "
            "reached the limit of requests of its plan."
        )
        try:
            liked_on_x = self._x_react(tweet_ref, like)
        except TooManyRequests as exManyRequest:
            self.account_id._get_message_many_requests(exManyRequest, endpoint="like")
            answer["message"] = quota_message
            return answer
        except Unauthorized as error:
            answer["message"] = self._x_refused_credentials_message(error)
            return answer
        except Forbidden as error:
            answer["message"] = self._x_forbidden_message(error)
            return answer
        except Exception as exp:  # noqa: BLE001 - tweepy may fail in any way
            # X reports a tweet that is gone as a partial error, the same one
            # it answers for a reference it does not know, so the publication
            # itself is asked about instead of reading the error.
            answer["post_deleted"] = self._remote_post_gone_on_action()
            answer["message"] = (
                _("The post does not exist or has been deleted.")
                if answer["post_deleted"]
                else _("Error Recommend Tweet: %(error)s", error=exp)
            )
            _logger.exception("Error reacting to tweet %s", tweet_ref)
            return answer
        if liked_on_x is None:
            answer["message"] = quota_message
            return answer
        answer.update(success=True, liked=liked_on_x)
        return answer

    def _x_react_post(self, like):
        """Give or withdraw the like of the account on this publication.

        :param like: ``True`` to give the like, ``False`` to withdraw it.
        :return: the answer of :meth:`_x_reaction_answer`.
        :rtype: dict
        """
        answer = self._x_reaction_answer(self.remote_ref, like, self.liked_by_account)
        # Read back on every import, so the write is only what keeps the card
        # in step between two of them.
        if answer["liked"] != self.liked_by_account:
            self.liked_by_account = answer["liked"]
        return answer

    def _x_react_comment(self, comment_ref, like):
        """Give or withdraw the like of the account on a comment.

        Nothing is stored: what the dialog draws is read again from X every
        time it opens.

        :param comment_ref: identifier of the comment on X.
        :param like: ``True`` to give the like, ``False`` to withdraw it.
        :return: the answer of :meth:`_x_reaction_answer`, with ``liked`` set
            to ``None`` unless X said, so an error that names nothing does
            not redraw the entry.
        :rtype: dict
        """
        if not comment_ref:
            return {
                "success": False,
                "message": _("The comment cannot be recommended on X."),
                "post_deleted": False,
                "liked": None,
            }
        return self._x_reaction_answer(comment_ref, like, None)

    def action_like_post(self, author_urn=None):
        # ``author_urn`` is accepted by contract and ignored: a call from the
        # client does not choose on behalf of whom the like is given.
        res = super().action_like_post(author_urn)
        if self.account_id.media_type == "x":
            return self._x_react_post(True)
        return res

    def action_unlike_post(self, author_urn=None):
        res = super().action_unlike_post(author_urn)
        if self.account_id.media_type == "x":
            return self._x_react_post(False)
        return res

    def action_like_comment(self, comment_ref=None, author_urn=None):
        res = super().action_like_comment(comment_ref, author_urn)
        if self.account_id.media_type == "x":
            return self._x_react_comment(comment_ref, True)
        return res

    def action_unlike_comment(self, comment_ref=None, author_urn=None):
        res = super().action_unlike_comment(comment_ref, author_urn)
        if self.account_id.media_type == "x":
            return self._x_react_comment(comment_ref, False)
        return res

    def delete_comment(self, comment_ref):
        """Delete a comment the account wrote on this publication.

        On X a comment is a tweet, and X only deletes the tweets of the
        account that asks, so the call is the one that deletes a publication,
        with the user context of the account. The client only offers it on the
        comments the account wrote.

        A tweet that is already gone counts as deleted: what was asked for is
        done. Nothing raises from here, because the client waits for a dict.

        :param comment_ref: identifier of the comment on X.
        :return: ``success`` and, on a failure, the ``message`` to show.
        :rtype: dict
        """
        if self.account_id.media_type != "x":
            return super().delete_comment(comment_ref)
        quota_answer = {
            "success": False,
            "message": _(
                "The comment could not be deleted on X. The account may have "
                "reached the limit of requests of its plan."
            ),
        }
        try:
            if not self.account_id._valid_time_request(endpoint="delete_comment"):
                return quota_answer
            response = self.account_id.get_client_api().delete_tweet(comment_ref)
        except TooManyRequests as exManyRequest:
            self.account_id._get_message_many_requests(
                exManyRequest, endpoint="delete_comment"
            )
            return quota_answer
        except NotFound:
            return {"success": True}
        except Unauthorized as error:
            return {
                "success": False,
                "message": self._x_refused_credentials_message(error),
            }
        except Forbidden as error:
            # Also what X answers for a tweet of another account.
            return {"success": False, "message": self._x_forbidden_message(error)}
        except Exception as exp:  # noqa: BLE001 - tweepy may fail in any way
            _logger.exception("Error deleting the comment %s on X", comment_ref)
            return {
                "success": False,
                "message": _("Error Delete Comment: %(error)s", error=exp),
            }
        data = getattr(response, "data", None) or {}
        if data.get("deleted") or self._is_x_not_found(response):
            return {"success": True}
        _logger.warning(
            "X did not delete the comment %(comment)s: %(errors)s",
            {"comment": comment_ref, "errors": response.errors},
        )
        return {
            "success": False,
            "message": _(
                "X did not delete the comment: %(errors)s",
                errors=", ".join(str(error) for error in response.errors or []),
            ),
        }

    @api.model
    def _x_media_download_url(self, media_type, url, variants):
        """Return the address a media of a tweet is downloaded from.

        A photo is downloaded from its ``url``. A video or an animated GIF
        has none: X lists its files as ``variants``, and the mp4 with the
        highest ``bit_rate`` is the best quality Odoo can play. A variant
        without ``bit_rate`` counts as zero, which is how X sends the single
        mp4 of an animated GIF.

        :param media_type: the ``type`` X reports for the media.
        :param url: the ``url`` X reports, only present for a photo.
        :param variants: the ``variants`` X reports, only present for a video
            or an animated GIF.
        :return: the address, or ``False`` when there is nothing to download.
        :rtype: str or bool
        """
        if media_type not in _VIDEO_MEDIA_TYPES_X:
            return url or False
        mp4_variants = [
            variant
            for variant in variants or []
            if variant.get("content_type") == _VIDEO_CONTENT_TYPE_X
            and variant.get("url")
        ]
        if not mp4_variants:
            return False
        return max(mp4_variants, key=lambda variant: variant.get("bit_rate") or 0)[
            "url"
        ]

    def _get_assets_save_x(self, media_keys, media_map):
        """Download the media of a tweet that are not stored yet.

        The photos go through :meth:`_store_remote_medias` and the videos and
        animated GIFs through :meth:`_store_remote_videos`, typed as the mp4
        X serves: their attachment is named after the media key, which has no
        extension to tell an mp4 by.

        :param media_keys: the media keys of the tweet, in the order X lists
            them.
        :param media_map: ``{media_key: (media_key, url, type, variants)}``,
            the media of the page as X reported them.
        :return: The images and the videos created, and the media key of each
            one, keyed by its identifier. They all go into the same write, so
            that a downloaded media is never stored without the reference
            telling it apart from one attached in Odoo.
        :rtype: tuple
        """
        medias_exist = self._get_medias_account(media_keys)
        image_url_by_ref = {}
        video_url_by_ref = {}
        for media_key in media_keys:
            if media_key in medias_exist or media_key not in media_map:
                continue
            _media_key, url, media_type, variants = media_map[media_key]
            download_url = self._x_media_download_url(media_type, url, variants)
            if media_type in _VIDEO_MEDIA_TYPES_X:
                video_url_by_ref[media_key] = download_url
            else:
                image_url_by_ref[media_key] = download_url
        images, media_refs = self._store_remote_medias(image_url_by_ref)
        videos, video_refs = self._store_remote_videos(
            video_url_by_ref, mimetype=_VIDEO_CONTENT_TYPE_X
        )
        return images, videos, {**media_refs, **video_refs}
