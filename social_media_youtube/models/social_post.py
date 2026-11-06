# Copyright 2026 Domatix <https://www.domatix.cloud>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class SocialPost(models.Model):
    """YouTube requirements on the posts to publish."""

    _inherit = "social.post"

    youtube_privacy_status = fields.Selection(
        [
            ("public", "Public"),
            ("unlisted", "Unlisted"),
            ("private", "Private"),
        ],
        string="YouTube Privacy",
        default="private",
        required=True,
        help="Visibility of the video on YouTube. Private keeps it visible only to "
        "the channel owner until it is published in YouTube Studio.",
    )
    has_youtube_account = fields.Boolean(compute="_compute_has_youtube_account")

    @api.depends("account_ids.media_id.media_type")
    def _compute_has_youtube_account(self):
        for post in self:
            post.has_youtube_account = any(
                account.media_id.media_type == "youtube" for account in post.account_ids
            )

    def _get_post_errors(self, media_type, account=None):
        """YouTube requires a video to publish."""
        errors = super()._get_post_errors(media_type, account=account)
        if media_type == "youtube" and not self.video_ids:
            errors.append(
                self.env._("You have to upload a video when posting on YouTube.")
            )
        return errors
