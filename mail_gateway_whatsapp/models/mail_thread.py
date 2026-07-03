# Copyright 2022 CreuBlanca
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import re

from odoo import models
from odoo.exceptions import UserError


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
        sanitized_number = self._phone_format(number=self[field_name])
        if not sanitized_number:
            raise UserError(self.env._("Phone cannot be sanitized"))
        # Keep only digits so outbound token never contains spaces or formatting chars.
        sanitized_number = re.sub(r"\D", "", sanitized_number)
        if not sanitized_number:
            raise UserError(self.env._("Phone cannot be sanitized"))
        partner = self._whatsapp_get_partner()
        # WhatsApp Cloud API expects recipient phone number in `to`.
        # Keep gateway token based on wa_id (phone digits) for outbound messages.
        token = sanitized_number
        if not self.env["res.partner.gateway.channel"].search(
            [
                ("partner_id", "=", partner.id),
                ("gateway_id", "=", gateway.id),
                ("gateway_token", "=", token),
            ]
        ):
            self.env["res.partner.gateway.channel"].create(
                {
                    "name": gateway.name,
                    "partner_id": partner.id,
                    "gateway_id": gateway.id,
                    "gateway_token": token,
                }
            )
        return self.env["mail.gateway.whatsapp"]._get_channel(
            gateway,
            token,
            {
                "contacts": [
                    {
                        "wa_id": sanitized_number,
                        "profile": {
                            "name": partner.display_name,
                            "user_id": partner.whatsapp_user_id,
                            "username": partner.whatsapp_username,
                        },
                    }
                ],
                "messages": [{"from": token}],
            },
            force_create=True,
        )

    def _whatsapp_get_partner(self):
        if "partner_id" in self._fields:
            return self.partner_id
        return None
