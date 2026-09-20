# Copyright 2025 Binhex <https://www.binhex.cloud>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import itertools
import logging

from tweepy.errors import TooManyRequests

from odoo import fields, models
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class SocialPostAccount(models.Model):
    _inherit = "social.post.account"

    x_post_account_id = fields.Char()
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
                            "x_post_account_id": post_account_id,
                            "post_account_url": f"https://x.com/{post_account.account_id.username}/status/{post_account_id}",
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
                return_message = self.env._(
                    "Error Get Comments for Tweet: %(error)s)", error=e
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
                return_message = self.env._(
                    "Error Comment Tweet: %(error)s)", error=exp
                )
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
                message_error = self.env._("Error Get Comment Post: %(error)s", error=e)
            if message_error:
                raise ValidationError(message_error)
            return True
        return False

    def _delete_post_account(self):
        if self.media_id.media_type == "x":
            message_error = ""
            try:
                result = self.account_id._valid_time_request(endpoint="delete_post")
                if result and self.x_post_account_id:
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
                message_error = self.env._("Error Delete Post X: %(error)s", error=e)
            if message_error:
                raise ValidationError(message_error)
        return super()._delete_post_account()

    def _get_assets_save_x(self, media_keys, media_map):
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
