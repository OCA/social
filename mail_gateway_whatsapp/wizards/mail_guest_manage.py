# Copyright 2025 Marcel Savegnago - Escodoo
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import models


class MailGuestManage(models.TransientModel):
    _inherit = "mail.guest.manage"

    def _merge_partner(self, partner):
        super()._merge_partner(partner)
        gateway_channel = self.env["res.partner.gateway.channel"].search(
            [
                ("partner_id", "=", partner.id),
                ("gateway_id.gateway_type", "=", "whatsapp"),
            ],
            limit=1,
        )
        if gateway_channel:
            partner.mobile = gateway_channel.gateway_token
            partner._onchange_mobile_validation()
        return True
