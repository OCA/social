# Copyright 2022 Creu Blanca
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
import logging

from odoo import fields, models
from odoo.http import request

_logger = logging


class MailBroker(models.Model):
    _inherit = "mail.broker"

    whatsapp_security_key = fields.Char()
    broker_type = fields.Selection(selection_add=[("whatsapp", "WhatsApp")])
    whatsapp_from_phone = fields.Char()

    def _set_webhook(self):
        super(MailBroker, self)._set_webhook()

    def _remove_webhook(self):
        super(MailBroker, self)._remove_webhook()

    def _get_channel_vals(self, token, update):
        result = super(MailBroker, self)._get_channel_vals(token, update)
        if self.broker_type == "whatsapp" and not result.get("name"):
            for contact in update.get("contacts"):
                if contact["wa_id"] == token:
                    result["name"] = contact["profile"]["name"]
                    continue
        return result

    def _receive_update_whatsapp(self, update):
        chat = {}
        if update:
            for entry in update["entry"]:
                for change in entry["changes"]:
                    if change["field"] != "messages":
                        continue
                    for message in change["value"].get("messages", []):
                        chat = self._get_channel(
                            message["from"], change["value"], force_create=True
                        )
        if not chat:
            return
        return chat.whatsapp_update(update)

    def _verify_bot(self, **kwargs):
        self.ensure_one()
        if self.broker_type != "whatsapp":
            return super()._verify_bot()
        response = request.make_response(kwargs.get("hub").get("challenge"))
        response.status_code = 200
        return response
