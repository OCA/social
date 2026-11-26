# Copyright 2026 Domatix <https://www.domatix.cloud>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import models


class SocialPost(models.Model):
    """TikTok requirements on the posts to publish."""

    _inherit = "social.post"

    def _get_post_errors(self, media_type, account=None):
        """TikTok publishes videos only, so a post without one is rejected."""
        errors = super()._get_post_errors(media_type, account=account)
        if media_type == "tiktok" and not self.video_ids:
            errors.append(
                self.env._(
                    "TikTok only supports video posts. Please add a video "
                    "or remove the TikTok accounts from this post."
                )
            )
        return errors

    def _get_post_warnings(self, media_type, account=None):
        """Say that the images of a post with a video never reach TikTok."""
        warnings = super()._get_post_warnings(media_type, account=account)
        if media_type == "tiktok" and self.image_ids and self.video_ids:
            warnings.append(
                self.env._(
                    "You have selected images and videos for this post. "
                    "TikTok only publishes videos, so the images will be ignored."
                )
            )
        return warnings
