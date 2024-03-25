# Copyright 2024 Dixmit
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


class WhatsappThreadComposer(models.TransientModel):
    _name = "whatsapp.thread.composer"

    partner_id = fields.Many2one("res.partner", required=True)
    broker_channel_id = fields.Many2one(
        "res.partner.broker.channel",
        required=True,
    )
    body = fields.Html(required=True)
    model = fields.Char(required=True)
    res_id = fields.Integer(required=True)

    def _get_message_vals(self):
        return {
            "body": self.body,
            "author_id": self.env.user.partner_id.id,
            "message_type": "comment",
        }

    def send(self):
        self.ensure_one()
        record = self.env[self.model].browse(self.res_id).exists()
        if not record:
            return
        message = record.message_post(**self._get_message_vals())
        message._send_to_broker_thread(self.broker_channel_id)
        self.env["bus.bus"]._sendone(
            self.env.user.partner_id,
            "mail.message/notification_update",
            {"elements": message.message_format()},
        )
