# Copyright 2022 CreuBlanca
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import _, models
from odoo.exceptions import UserError

from odoo.addons.phone_validation.tools import phone_validation


class MailThread(models.AbstractModel):

    _inherit = "mail.thread"

    def _get_whatsapp_channel_vals(self, token, broker, partner):
        result = {
            "token": token,
            "broker_id": broker.id,
            "show_on_app": broker.show_on_app,
        }
        if partner:
            result["partner_id"] = partner.id
            result["name"] = partner.display_name
        return result

    def _whatsapp_get_channel(self, field_name, broker):
        phone = self[field_name]
        sanitize_res = phone_validation.phone_sanitize_numbers_w_record([phone], self)
        sanitized_number = sanitize_res[phone].get("sanitized")
        if not sanitized_number:
            raise UserError(_("Phone cannot be sanitized"))
        sanitized_number = sanitized_number[1:]
        channel = broker._get_channel_id(sanitized_number)
        partner = self._whastapp_get_partner()
        if not channel:
            channel = self.env["mail.broker.channel"].create(
                self._get_whatsapp_channel_vals(sanitized_number, broker, partner)
            )
        else:
            channel = self.env["mail.broker.channel"].browse(channel)
        if not channel.partner_id and partner:
            channel.partner_id = partner
        return channel

    def _whastapp_get_partner(self):
        if self._name == "res.partner":
            return self
        if "partner_id" in self._fields:
            return self.partner_id
