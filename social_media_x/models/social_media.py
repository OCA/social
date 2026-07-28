# Copyright 2025 Binhex <https://www.binhex.cloud>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


class SocialMedia(models.Model):
    """Registers X as an available social media."""

    _inherit = "social.media"

    media_type = fields.Selection(selection_add=[("x", "X")])

    def open_action_account(self):
        res = super().open_action_account()
        if self.media_type == "x":
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
