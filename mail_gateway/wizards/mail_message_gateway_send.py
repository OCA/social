# Copyright 2024 Dixmit
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


class MailMessageGatewaySend(models.TransientModel):
    _name = "mail.message.gateway.send"
    _description = "Send Message through gateway"

    message_id = fields.Many2one("mail.message", required=True)
    partner_id = fields.Many2one("res.partner", required=True)
    gateway_channel_id = fields.Many2one(
        "res.partner.gateway.channel",
        required=True,
    )

    def send(self):
        self.message_id._send_to_gateway_thread(self.gateway_channel_id)
