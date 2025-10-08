# Copyright 2025 Binhex <https://www.binhex.cloud>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import base64
import itertools
import logging

import requests
from tweepy.errors import TooManyRequests

from odoo import Command, _, fields, models
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class SocialPostAccount(models.Model):
    _inherit = "social.post.account"

    x_post_account_id = fields.Char()
    x_post_url = fields.Char()
    retweet_count = fields.Integer(default=0)
    quote_count = fields.Integer(default=0)

    def _action_post(self):
        res = super()._action_post()
        if any(account.media_type == "x" for account in self.post_id.account_ids):
            post_accounts = self.filter_by_media_types(["x"])
            for post_account in post_accounts:
                post_account_id = post_account.account_id.create_tweet(
                    message=post_account.message,
                    image_ids=post_account.image_ids,
                )
                if post_account_id:
                    post_account.write(
                        {
                            "x_post_account_id": post_account_id,
                            "post_account_url": f"https://x.com/{post_account.account_id.username}/status/{post_account_id}",
                            "published_date": fields.Datetime.now(),
                            "state": "posted",
                        }
                    )
        return res

    def get_comments(self):
        data = super().get_comments()
        comments = []
        if "x" == self.account_id.media_type:
            try:
                result = self.account_id._valid_time_request(endpoint="get_comments")
                if result:
                    client_api = self.account_id.get_client_api(
                        bearer_token=self.account_id.x_access_token_oauth2
                    )
                    query = (
                        f"conversation_id:{self.x_post_account_id} "
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
                    )
                    if response.data:
                        comments = []
                        users = {
                            str(u.id): u
                            for u in (response.includes.get("users", []) or [])
                        }
                        for comment in response.data or []:
                            author = users.get(str(comment.author_id))
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
                                        val.get("media_key", {})
                                        for val in comment.get("includes", {}).get(
                                            "media", {}
                                        )
                                    ],
                                }
                            )

            except TooManyRequests as exManyRequest:
                self.account_id._get_message_many_requests(
                    exManyRequest, endpoint="get_comments"
                )
            except Exception as e:
                return_message = _("Error Get Comments for Tweet: %(error)s)") % {
                    "error": e,
                }
                _logger.error(return_message)
                return {
                    "success": False,
                    "message": return_message,
                }
        return {
            "success": True,
            "data": list(itertools.chain(data.get("data", []), comments)),
        }

    def create_x_comment(self, post_data):
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
                            in_reply_to_tweet_id=self.x_post_account_id,
                            media_ids=media_ids,
                        )
                    else:
                        client_api.create_tweet(
                            text=post_data.get("body", ""),
                            in_reply_to_tweet_id=self.x_post_account_id,
                        )
            except TooManyRequests as exManyRequest:
                self.account_id._get_message_many_requests(
                    exManyRequest, endpoint="create_comment"
                )
            except Exception as exp:
                return_message = _("Error Comment Tweet: %(error)s)") % {
                    "error": exp,
                }
                _logger.error(return_message)
                return {
                    "success": False,
                    "message": return_message,
                }
        return {
            "success": True,
        }

    def create_comment(self, post_data, context=None):
        if "x" == self.account_id.media_type:
            result = self.create_x_comment(post_data)
            return result
        else:
            return super().create_comment(post_data, context)

    def get_post_x(self):
        if "x" == self.account_id.media_type and self.x_post_account_id:
            message_error = ""
            try:
                result = self.account_id._valid_time_request(endpoint="get_post")
                if result:
                    client_api = self.account_id.get_client_api(
                        bearer_token=self.account_id.x_access_token_oauth2
                    )
                    response = client_api.get_tweet(
                        self.x_post_account_id, tweet_fields=["id"]
                    )
                    if response.errors:
                        message_error = ", ".join(response.errors)
            except TooManyRequests as exManyRequest:
                self.account_id._get_message_many_requests(
                    exManyRequest, endpoint="get_post"
                )
            except Exception as e:
                message_error = _("Error Get Comment Post: %(error)s") % {
                    "error": e,
                }
                _logger.error(message_error)
            if message_error:
                raise ValidationError(message_error)
            return True
        return False

    def _delete_post_account(self):
        res = super()._delete_post_account()
        if self.media_id.media_type == "x":
            message_error = ""
            try:
                result = self.account_id._valid_time_request(endpoint="delete_post")
                if result:
                    client_api = self.account_id.get_client_api(
                        bearer_token=self.account_id.x_access_token_oauth2
                    )
                    response = client_api.delete_tweet(self.x_post_account_id)
                    if response.errors:
                        message_error = ", ".join(response.errors)
            except TooManyRequests as exManyRequest:
                self.account_id._get_message_many_requests(
                    exManyRequest, endpoint="delete_post"
                )
            except Exception as e:
                message_error = _("Error Delete Post X: %(error)s") % {
                    "error": e,
                }
                _logger.error(message_error)
            if message_error:
                raise ValidationError(message_error)
        return res

    def _get_assets_save_x(self, media_keys, media_map):
        attachments = []
        medias_exist = (
            self.env["ir.attachment"]
            .search(
                [
                    ("name", "in", media_keys),
                ]
            )
            .mapped("name")
        )
        for media in media_keys:
            if media not in medias_exist and media_map.get(media, False):
                media_content = requests.get(media_map.get(media, False)[1], timeout=30)
                if media_content.status_code == 200:
                    mimetype = (
                        "image/jpeg"
                        if media_map.get(media, False)[2] == "photo"
                        else "video/mp4"
                    )
                    attachments.append(
                        Command.create(
                            {
                                "name": media,
                                "type": "binary",
                                "mimetype": mimetype,
                                "res_model": self._name,
                                "res_id": self.id,
                                "datas": base64.b64encode(media_content.content),
                            }
                        )
                    )
        return attachments
