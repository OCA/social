# Copyright 2021 Creu Blanca
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import fields, models


class MailBroker(models.Model):

    _inherit = "mail.broker"

    telegram_security_key = fields.Char()
    broker_type = fields.Selection(selection_add=[("telegram", "Telegram")])
