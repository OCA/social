# Copyright 2025 Binhex <https://www.binhex.cloud>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import itertools
import logging

from tweepy.errors import TooManyRequests

from odoo import _, fields, models
from odoo.exceptions import UserError

from ..social_x_utils import _URL_X

_logger = logging.getLogger(__name__)


class SocialPostAccount(models.Model):
    """Publication, comments and statistics of a post on an X account."""

    _inherit = "social.post.account"

    x_post_url = fields.Char()
    retweet_count = fields.Integer(default=0)
    quote_count = fields.Integer(default=0)

    def _action_post(self, post_id):
        res = super()._action_post(post_id)
        if any(account.media_type == "x" for account in post_id.account_ids):
            post_accounts = post_id.filter_by_media_types(["x"])
            for post_account in post_accounts:
                post_account_id = post_account.account_id.create_tweet(
                    message=post_account.message,
                    image_ids=post_account.post_id.image_ids,
                    video_ids=post_account.post_id.video_ids,
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
                        }
                    )
                else:
                    post_account.write(
                        {
                            "state": "failed",
                        }
                    )
        return res

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
                                    "id": comment.id,
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

            except TooManyRequests as exManyRequest:
                self.account_id._get_message_many_requests(
                    exManyRequest, endpoint="get_comments"
                )
            except Exception as e:
                return_message = _("Error Get Comments for Tweet: %(error)s)", error=e)
                _logger.exception(return_message)
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
                            in_reply_to_tweet_id=self.remote_ref,
                            media_ids=media_ids,
                        )
                    else:
                        client_api.create_tweet(
                            text=post_data.get("body", ""),
                            in_reply_to_tweet_id=self.remote_ref,
                        )
            except TooManyRequests as exManyRequest:
                self.account_id._get_message_many_requests(
                    exManyRequest, endpoint="create_comment"
                )
            except Exception as exp:
                return_message = _("Error Comment Tweet: %(error)s)", error=exp)
                _logger.exception(return_message)
                return {
                    "success": False,
                    "message": return_message,
                }
        return {
            "success": True,
        }

    def create_comment(self, post_data, context=None):
        if "x" == self.account_id.media_type:
            return self.create_x_comment(post_data)
        else:
            return super().create_comment(post_data, context)

    def get_post_x(self):
        """Check that this post still exists on X.

        :rtype: bool
        """
        if "x" == self.account_id.media_type and self.remote_ref:
            message_error = ""
            try:
                result = self.account_id._valid_time_request(endpoint="get_post")
                if result:
                    client_api = self.account_id.get_client_api(
                        bearer_token=self.account_id.sudo().x_access_token_oauth2
                    )
                    response = client_api.get_tweet(
                        self.remote_ref, tweet_fields=["id"]
                    )
                    if response.errors:
                        message_error = ", ".join(response.errors)
            except TooManyRequests as exManyRequest:
                self.account_id._get_message_many_requests(
                    exManyRequest, endpoint="get_post"
                )
            except Exception as e:
                message_error = _("Error Get Comment Post: %(error)s", error=e)
                _logger.exception(message_error)
            if message_error:
                raise UserError(message_error)
            return True
        return False

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
            except Exception as e:
                message_error = _("ERROR DELETE POST X: %(error)s", error=e)
                _logger.exception(message_error)
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
                attachments.append(
                    self._map_medias_account(
                        **{"name": media, "url": media_map.get(media, False)[1]},
                    )
                )
        return attachments
