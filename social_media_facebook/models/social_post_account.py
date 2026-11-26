# Copyright 2026 Domatix <https://www.domatix.cloud>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import logging

import requests

from odoo import models

from ..social_facebook_utils import _GRAPH_VERSION, _URL_GRAPH

_logger = logging.getLogger(__name__)

# The comments endpoint pages at 100; the pass stops after this many pages.
_COMMENTS_MAX_PAGES = 10


class SocialPostAccount(models.Model):
    """Facebook implementation of the post account actions."""

    _inherit = "social.post.account"

    def _action_post(self, post_id):
        res = super()._action_post(post_id)
        if any(account.media_type == "facebook" for account in post_id.account_ids):
            for post_account in post_id._filter_by_media_types(["facebook"]):
                with post_account._publish_guard():
                    post_account._check_publishable()
                    post_id_remote = post_account._publish_attempt(
                        post_account.account_id._post_facebook,
                        post_account=post_account,
                    )
                    if post_id_remote:
                        post_account._register_publish_success(
                            post_id_remote,
                            f"https://www.facebook.com/{post_id_remote}",
                            False,
                            bool(post_id.video_ids),
                        )
                    else:
                        post_account._register_publish_refused(
                            self.env._(
                                "Facebook did not return a reference for the "
                                "publication."
                            )
                        )
        return res

    def _delete_post_account(self):
        if self.media_type != "facebook":
            return super()._delete_post_account()
        return self.account_id._delete_facebook_post(self)

    def _supports_comments(self):
        if self.media_type != "facebook":
            return super()._supports_comments()
        return True

    def get_comments(self):
        if self.media_type != "facebook":
            return super().get_comments()
        try:
            comments = []
            url = f"{_URL_GRAPH}{_GRAPH_VERSION}/{self.remote_ref}/comments"
            params = {
                "access_token": self.account_id.sudo().facebook_access_token,
                "fields": "id,message,created_time,from",
                "limit": 100,
            }
            for _page in range(_COMMENTS_MAX_PAGES):
                response = requests.get(url, params=params, timeout=30)
                if response.status_code != 200:
                    raise ValueError(response.text)
                payload = response.json()
                comments.extend(payload.get("data", []))
                url = payload.get("paging", {}).get("next")
                params = {}
                if not url:
                    break
            data = [
                {
                    "id": comment.get("id"),
                    "text": comment.get("message"),
                    "actor": comment.get("from", {}).get("name"),
                    "published_time": comment.get("created_time"),
                    "images_url": [],
                }
                for comment in comments
            ]
            return {"success": True, "data": data}
        except Exception as e:
            message = self.env._(
                "Error Get Comments for Facebook post: %(error)s", error=e
            )
            _logger.exception(message)
            return {"success": False, "message": message}

    def create_comment(self, post_data, context=None):
        if self.media_type != "facebook":
            return super().create_comment(post_data, context)
        try:
            response = requests.post(
                f"{_URL_GRAPH}{_GRAPH_VERSION}/{self.remote_ref}/comments",
                data={
                    "access_token": self.account_id.sudo().facebook_access_token,
                    "message": post_data.get("body", ""),
                },
                timeout=30,
            )
            if response.status_code != 200:
                raise ValueError(response.text)
            return {"success": True, "id": response.json().get("id")}
        except Exception as e:
            message = self.env._("Error Comment Facebook: %(error)s", error=e)
            _logger.exception(message)
            return {"success": False, "message": message}

    def delete_facebook_comment(self, comment_id):
        """Delete a comment on Facebook, called by the JS service."""
        try:
            response = requests.delete(
                f"{_URL_GRAPH}{_GRAPH_VERSION}/{comment_id}",
                params={"access_token": self.account_id.sudo().facebook_access_token},
                timeout=30,
            )
            if response.status_code != 200:
                raise ValueError(response.text)
            return {"success": True, "message": ""}
        except Exception as e:
            message = self.env._("Error Delete Comment Facebook: %(error)s", error=e)
            _logger.exception(message)
            return {"success": False, "message": message}
