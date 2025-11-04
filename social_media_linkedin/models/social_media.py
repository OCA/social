# Copyright 2025 Binhex <https://www.binhex.cloud>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).


from odoo import fields, models

from ..social_linkedin_utils import _HEADERS_LINKEDIN


class SocialMedia(models.Model):
    _inherit = "social.media"

    media_type = fields.Selection(
        selection_add=[("linkedin", "Linkedin")], default="linkedin"
    )

    def _get_linkedin_headers(self, access_token=None, content_type=None):
        headers = _HEADERS_LINKEDIN
        if access_token:
            headers.update({"Authorization": f"Bearer {access_token}"})
        if content_type:
            headers.update({"Content-Type": content_type})
        return headers

    def open_action_account(self):
        res = super().open_action_account()
        if self.media_type == "linkedin":
            return {
                "res_model": "wizard.social.account",
                "views": [[False, "form"]],
                "target": "new",
                "type": "ir.actions.act_window",
                "context": {
                    "default_media_id": self.id,
                },
            }
        return res
