# Copyright 2020 Creu Blanca
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, models


class MailBrokerChannel(models.Model):

    _inherit = "mail.broker.channel"

    @api.returns("mail.message.broker", lambda value: value.id)
    def telegram_message_post_broker(self, body=False, **kwargs):
        return self.message_post_broker(body=body, broker_type="telegram", **kwargs)
