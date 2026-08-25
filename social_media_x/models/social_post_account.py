# Copyright 2026 Binhex <https://www.binhex.cloud>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import itertools
import logging
from collections import Counter

from tweepy.errors import TooManyRequests

from odoo import _, fields, models
from odoo.exceptions import UserError
from odoo.tools import plaintext2html

from ..social_x_utils import _URL_X

_logger = logging.getLogger(__name__)


class SocialPostAccount(models.Model):
    """Publication, comments and statistics of a post on an X account."""

    _inherit = "social.post.account"

    def _action_post(self, post_id):
        res = super()._action_post(post_id)
        if any(account.media_type == "x" for account in post_id.account_ids):
            post_accounts = post_id._filter_by_media_types(["x"])
            images, videos = post_id._medias_for_publication()
            for post_account in post_accounts:
                with post_account._publish_guard():
                    post_account._check_publishable()
                    post_account_id = post_account._publish_attempt(
                        post_account.account_id.create_tweet,
                        message=post_account.message,
                        image_ids=images,
                        video_ids=videos,
                        post_id=post_id,
                        post_account_id=post_account,
                    )
                    if post_account_id:
                        post_account.write(
                            {
                                "remote_ref": post_account_id,
                                "post_account_url": (
                                    f"{_URL_X}{post_account.account_id.username}"
                                    f"/status/{post_account_id}"
                                ),
                                "state": "posted",
                                "published_date": fields.Datetime.now(),
                                "failed_description": False,
                            }
                        )
                    else:
                        post_account.write(
                            {
                                "state": "failed",
                                "failed_description": plaintext2html(
                                    _(
                                        "X did not accept the post. The "
                                        "account may have reached the limit "
                                        "of requests of its plan: check the "
                                        "account and try again later."
                                    )
                                ),
                            }
                        )
        return res

    def _x_comment_parent_ref(self, tweet, comment_refs):
        """Return the comment a tweet of the thread answers.

        The search that reads the comments asks for the whole conversation, so
        the replies of a reply arrive in the same answer as the comments of
        the post. What tells them apart is already in the payload: the
        ``replied_to`` reference of a comment is the post, and that of a reply
        is another tweet of the list.

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
                if result:
                    client_api = self.account_id.get_client_api(
                        bearer_token=self.account_id.sudo().x_access_token_oauth2
                    )
                    query = (
                        f"conversation_id:{self.remote_ref} "
                        f"is:reply -is:retweet -is:quote"
                    )
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
                    )
                    if response.data:
                        comments = []
                        comment_refs = {str(tweet.id) for tweet in response.data}
                        users = {
                            str(u.id): u
                            for u in (response.includes.get("users", []) or [])
                        }
                        media_urls = {
                            media.media_key: media.url
                            for media in (response.includes.get("media") or [])
                            if media.url
                        }
                        for comment in response.data or []:
                            author = users.get(str(comment.author_id))
                            media_keys = (
                                getattr(comment, "attachments", {}) or {}
                            ).get("media_keys", [])
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
                                    "published_time": comment.created_at,
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
                        # The whole thread already arrived, so how many
                        # replies each comment has is counted here and never
                        # asked to X again.
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
            "data": list(itertools.chain(data.get("data", []), comments)),
        }

    def create_x_comment(self, post_data):
        """Publish a reply to this post, with its attachments if any.

        :rtype: dict
        """
        if "x" == self.account_id.media_type:
            try:
                result = self.account_id._valid_time_request(endpoint="create_comment")
                if result:
                    client_api = self.account_id.get_client_api()
                    # A reply to a comment answers that tweet instead of the
                    # post: on X both are tweets and the only difference is
                    # which one is being replied to.
                    target = post_data.get("social_parent_ref") or self.remote_ref
                    if post_data.get("attachment_ids", False) and post_data.get(
                        "body", False
                    ):
                        attachment_ids = self.env["ir.attachment"].browse(
                            post_data.get("attachment_ids", [])
                        )
                        media_ids = self.account_id._prepare_medias_for_tweet(
                            image_ids=attachment_ids
                        )
                        client_api.create_tweet(
                            text=post_data.get("body", ""),
                            in_reply_to_tweet_id=target,
                            media_ids=media_ids,
                        )
                    else:
                        client_api.create_tweet(
                            text=post_data.get("body", ""),
                            in_reply_to_tweet_id=target,
                        )
            except TooManyRequests as exManyRequest:
                self.account_id._get_message_many_requests(
                    exManyRequest, endpoint="create_comment"
                )
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
        }

    def create_comment(self, post_data, context=None):
        if "x" == self.account_id.media_type:
            return self.create_x_comment(post_data)
        else:
            return super().create_comment(post_data, context)

    def _check_remote_post_exists(self):
        """Read the post on X to know whether it is still online.

        Only the ``Not Found`` answer of X is treated as a deletion. A
        throttled application or any other failure means the post could not
        be read, not that it is gone, so the record is left untouched.
        """
        if self.account_id.media_type != "x" or not self.remote_ref:
            return super()._check_remote_post_exists()
        try:
            if not self.account_id._valid_time_request(endpoint="get_post"):
                return True
            client_api = self.account_id.get_client_api(
                bearer_token=self.account_id.sudo().x_access_token_oauth2
            )
            response = client_api.get_tweet(self.remote_ref, tweet_fields=["id"])
        except TooManyRequests as exManyRequest:
            self.account_id._get_message_many_requests(
                exManyRequest, endpoint="get_post"
            )
            return True
        except Exception:  # noqa: BLE001 - unreachable is not deleted
            _logger.exception(
                "Error checking the X post %s, it is left untouched",
                self.remote_ref,
            )
            return True
        if self._is_x_not_found(response):
            self._register_remote_post_gone()
            return False
        if response.errors:
            _logger.warning(
                "X answered with errors while checking the post %(post)s, it "
                "is left untouched: %(errors)s",
                {"post": self.remote_ref, "errors": response.errors},
            )
        return True

    def _is_x_not_found(self, response):
        """Whether X answered that the post does not exist any more.

        X reports a deleted post as a partial error carrying the
        ``resource-not-found`` type instead of raising, so the answer has to
        be read rather than the exception caught.

        :param response: the ``tweepy.Response`` of a tweet read.
        :rtype: bool
        """
        return any(
            "resource-not-found" in str(error.get("type", ""))
            or "Not Found" in str(error.get("title", ""))
            for error in response.errors or []
            if isinstance(error, dict)
        )

    def _delete_post_account(self):
        if self.media_id.media_type == "x":
            message_error = ""
            try:
                result = self.account_id._valid_time_request(endpoint="delete_post")
                if result and self.remote_ref:
                    client_api = self.account_id.get_client_api(
                        bearer_token=self.account_id.sudo().x_access_token_oauth2
                    )
                    response = client_api.delete_tweet(self.remote_ref)
                    if response.errors:
                        message_error = ", ".join(response.errors)
            except TooManyRequests as exManyRequest:
                self.account_id._get_message_many_requests(
                    exManyRequest, endpoint="delete_post"
                )
            except Exception as e:  # noqa: BLE001 - tweepy may fail in any way
                message_error = _("ERROR DELETE POST X: %(error)s", error=e)
                _logger.exception("Error deleting tweet %s", self.remote_ref)
            if message_error:
                raise UserError(message_error)
        return super()._delete_post_account()

    def _get_assets_save_x(self, media_keys, media_map):
        """Return the attachment commands for the media not stored yet.

        :rtype: list
        """
        attachments = []
        medias_exist = self._get_medias_account(media_keys)
        for media in media_keys:
            if (
                media not in medias_exist
                and media_map.get(media, False)
                and media_map.get(media, False)[1]
            ):
                command = self._map_medias_account(
                    **{"name": media, "url": media_map.get(media, False)[1]},
                )
                if command:
                    attachments.append(command)
        return attachments
