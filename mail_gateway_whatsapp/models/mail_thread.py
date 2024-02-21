# Copyright 2022 CreuBlanca
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import _, models
from odoo.exceptions import UserError

from odoo.addons.phone_validation.tools import phone_validation


class MailThread(models.AbstractModel):

    _inherit = "mail.thread"

    def _get_whatsapp_channel_vals(self, token, gateway, partner):
        result = {
            "gateway_channel_token": token,
            "gateway_id": gateway.id,
        }
        if partner:
            result["partner_id"] = partner.id
            result["name"] = partner.display_name
        return result

    def _whatsapp_get_channel(self, field_name, gateway):
        phone = self[field_name]
        sanitize_res = phone_validation.phone_sanitize_numbers_w_record([phone], self)
        sanitized_number = sanitize_res[phone].get("sanitized")
        if not sanitized_number:
            raise UserError(_("Phone cannot be sanitized"))
        sanitized_number = sanitized_number[1:]
        partner = self._whatsapp_get_partner()
        if not self.env["res.partner.gateway.channel"].search(
            [
                ("partner_id", "=", partner.id),
                ("gateway_id", "=", gateway.id),
                ("gateway_token", "=", sanitized_number),
            ]
        ):
            self.env["res.partner.gateway.channel"].create(
                {
                    "name": gateway.name,
                    "partner_id": partner.id,
                    "gateway_id": gateway.id,
                    "gateway_token": sanitized_number,
                }
            )
        return self.env["mail.gateway.whatsapp"]._get_channel(
            gateway,
            sanitized_number,
            {
                "contacts": [
                    {
                        "wa_id": sanitized_number,
                        "profile": {"name": partner.display_name},
                    }
                ],
                "messages": [{"from": sanitized_number}],
            },
            force_create=True,
        )

    def _whatsapp_get_partner(self):
        if "partner_id" in self._fields:
            return self.partner_id
        return None
