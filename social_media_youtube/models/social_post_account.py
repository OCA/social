# Copyright 2026 Domatix <https://www.domatix.cloud>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import logging

import requests

from odoo import models

from ..social_youtube_utils import _URL_YOUTUBE_API

_logger = logging.getLogger(__name__)

# The comment threads endpoint pages at 100; the pass stops after this many pages.
_COMMENTS_MAX_PAGES = 10


class SocialPostAccount(models.Model):
    """YouTube implementation of the post account actions."""

    _inherit = "social.post.account"

    def _action_post(self, post_id):
        res = super()._action_post(post_id)
        if any(account.media_type == "youtube" for account in post_id.account_ids):
            for post_account in post_id._filter_by_media_types(["youtube"]):
                with post_account._publish_guard():
                    post_account._check_publishable()
                    video_id = post_account._publish_attempt(
                        post_account.account_id._post_youtube_video,
                        post_account=post_account,
                    )
                    if video_id:
                        post_account._register_publish_success(
                            video_id,
                            f"https://www.youtube.com/watch?v={video_id}",
                            False,
                            True,
                        )
                    else:
                        post_account._register_publish_refused(
                            self.env._(
                                "YouTube did not return a reference for the "
                                "publication."
                            )
                        )
        return res

    def _delete_post_account(self):
        if self.media_type != "youtube":
            return super()._delete_post_account()
        return self.account_id._delete_youtube_video(self)

    def _supports_comments(self):
        if self.media_type != "youtube":
            return super()._supports_comments()
        return True

    def get_comments(self):
        if self.media_type != "youtube":
            return super().get_comments()
        try:
            access_token = self.account_id._refresh_youtube_token()
            comments = []
            params = {
                "part": "snippet",
                "videoId": self.remote_ref,
                "maxResults": 100,
            }
            for _page in range(_COMMENTS_MAX_PAGES):
                response = requests.get(
                    f"{_URL_YOUTUBE_API}/youtube/v3/commentThreads",
                    params=params,
                    headers={"Authorization": f"Bearer {access_token}"},
                    timeout=30,
                )
                if response.status_code != 200:
                    raise ValueError(response.text)
                payload = response.json()
                comments.extend(payload.get("items", []))
                page_token = payload.get("nextPageToken")
                if not page_token:
                    break
                params = dict(params, pageToken=page_token)
            data = []
            for item in comments:
                top = item.get("snippet", {}).get("topLevelComment", {})
                snippet = top.get("snippet", {})
                data.append(
                    {
                        "id": top.get("id"),
                        "text": snippet.get("textOriginal")
                        or snippet.get("textDisplay"),
                        "actor": snippet.get("authorDisplayName"),
                        "author_image": snippet.get("authorProfileImageUrl"),
                        "published_time": snippet.get("publishedAt"),
                        "images_url": [],
                    }
                )
            return {"success": True, "data": data}
        except Exception as e:
            message = self.env._(
                "Error Get Comments for YouTube video: %(error)s", error=e
            )
            _logger.exception(message)
            return {"success": False, "message": message}

    def create_comment(self, post_data, context=None):
        if self.media_type != "youtube":
            return super().create_comment(post_data, context)
        try:
            access_token = self.account_id._refresh_youtube_token()
            response = requests.post(
                f"{_URL_YOUTUBE_API}/youtube/v3/commentThreads",
                params={"part": "snippet"},
                headers={"Authorization": f"Bearer {access_token}"},
                json={
                    "snippet": {
                        "videoId": self.remote_ref,
                        "topLevelComment": {
                            "snippet": {"textOriginal": post_data.get("body", "")}
                        },
                    }
                },
                timeout=30,
            )
            if response.status_code not in (200, 201):
                raise ValueError(response.text)
            payload = response.json()
            return {
                "success": True,
                "id": payload.get("snippet", {}).get("topLevelComment", {}).get("id"),
            }
        except Exception as e:
            message = self.env._("Error Comment YouTube: %(error)s", error=e)
            _logger.exception(message)
            return {"success": False, "message": message}

    def delete_youtube_comment(self, comment_id):
        """Delete a comment on YouTube, called by the JS service."""
        try:
            access_token = self.account_id._refresh_youtube_token()
            response = requests.delete(
                f"{_URL_YOUTUBE_API}/youtube/v3/comments",
                params={"id": comment_id},
                headers={"Authorization": f"Bearer {access_token}"},
                timeout=30,
            )
            if response.status_code not in (200, 204):
                raise ValueError(response.text)
            return {"success": True, "message": ""}
        except Exception as e:
            message = self.env._("Error Delete Comment YouTube: %(error)s", error=e)
            _logger.exception(message)
            return {"success": False, "message": message}
