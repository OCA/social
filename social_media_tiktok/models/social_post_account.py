# Copyright 2026 Domatix <https://www.domatix.cloud>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import logging

import requests

from odoo import models

from ..social_tiktok_utils import _URL_TIKTOK_API

_logger = logging.getLogger(__name__)


class SocialPostAccount(models.Model):
    """TikTok implementation of the post account actions."""

    _inherit = "social.post.account"

    def _check_remote_post_exists(self):
        """Whether the video is still on TikTok.

        A private publication carries no reference to query: it is not gone,
        it simply cannot be checked.
        """
        if self.media_type != "tiktok":
            return super()._check_remote_post_exists()
        if not self.remote_ref:
            return True
        try:
            response = requests.post(
                _URL_TIKTOK_API + "video/query/",
                headers=self.account_id._get_tiktok_headers(),
                params={"fields": "id"},
                json={"filters": {"video_ids": [self.remote_ref]}},
                timeout=60,
            )
            if response.status_code != 200:
                return True
            return bool(response.json().get("data", {}).get("videos"))
        except requests.RequestException:
            _logger.exception("Error querying the TikTok video")
            return True

    def _action_post(self, post_id):
        res = super()._action_post(post_id)
        if any(account.media_type == "tiktok" for account in post_id.account_ids):
            for post_account in post_id._filter_by_media_types(["tiktok"]):
                with post_account._publish_guard():
                    post_account._check_publishable()
                    published_ref = post_account._publish_attempt(
                        post_account.account_id._post_tiktok_video,
                        post_account=post_account,
                    )
                    if published_ref:
                        post_account._register_publish_success(
                            published_ref,
                            f"https://www.tiktok.com/"
                            f"@{post_account.account_id.tiktok_username}"
                            f"/video/{published_ref}",
                            False,
                            True,
                        )
                    elif published_ref is False:
                        # The video is online, but TikTok only hands its
                        # identifier back for a public post: an unaudited app
                        # publishes privately and nothing can be linked.
                        post_account._register_publish_success(
                            False, False, False, True
                        )
                        post_account.message_post(
                            body=self.env._(
                                "TikTok published the video with private "
                                "visibility and returned no public reference: "
                                "it will not be linked from here until the app "
                                "is audited by TikTok."
                            )
                        )
                    else:
                        post_account._register_publish_refused(
                            self.env._(
                                "TikTok did not return a reference for the publication."
                            )
                        )
        return res

    def _delete_post_account(self):
        if self.media_type != "tiktok":
            return super()._delete_post_account()
        return self.account_id._delete_tiktok_video(self)
