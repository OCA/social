# Copyright 2022 Creu Blanca
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class MailBroker(models.Model):
    _inherit = "mail.broker"

    whatsapp_security_key = fields.Char()
    broker_type = fields.Selection(selection_add=[("whatsapp", "WhatsApp")])
    whatsapp_from_phone = fields.Char()
