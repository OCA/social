# Copyright 2024 Dixmit
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


class MailMessageBrokerSend(models.TransientModel):

    _name = "mail.message.broker.send"
    _description = "Send Message through broker"

    message_id = fields.Many2one("mail.message", required=True)
    partner_id = fields.Many2one("res.partner", required=True)
    broker_channel_id = fields.Many2one(
        "res.partner.broker.channel",
        required=True,
    )

    def send(self):
        self.message_id._send_to_broker_thread(self.broker_channel_id)
