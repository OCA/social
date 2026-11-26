# Copyright 2026 Domatix <https://www.domatix.cloud>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


class SocialMedia(models.Model):
    """Registers TikTok as an available social media."""

    _inherit = "social.media"

    media_type = fields.Selection(selection_add=[("tiktok", "TikTok")])

    def action_open_account(self):
        res = super().action_open_account()
        if self.media_type == "tiktok":
            return {
                "name": self.env._("Associate %(media)s account", media=self.name),
                "res_model": "wizard.social.account",
                "views": [[False, "form"]],
                "target": "new",
                "type": "ir.actions.act_window",
                "context": {
                    "default_media_id": self.id,
                },
            }
        return res
