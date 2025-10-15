# Copyright 2025 Binhex <https://www.binhex.cloud>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models

from ..social_facebook_utils import _HEADERS_FACEBOOK


class SocialMedia(models.Model):
    _inherit = "social.media"

    media_type = fields.Selection(
        selection_add=[("facebook", "Facebook")], default="facebook"
    )

    def _get_facebook_headers(self, access_token=None):
        headers = _HEADERS_FACEBOOK.copy()
        if access_token:
            headers.update({"Authorization": "Bearer %s" % access_token})
        return headers

    def open_action_account(self):
        res = super().open_action_account()
        if self.media_type == "facebook":
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
