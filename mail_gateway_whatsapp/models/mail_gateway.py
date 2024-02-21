# Copyright 2022 Creu Blanca
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class MailGateway(models.Model):
    _inherit = "mail.gateway"

    whatsapp_security_key = fields.Char()
    gateway_type = fields.Selection(
        selection_add=[("whatsapp", "WhatsApp")], ondelete={"whatsapp": "cascade"}
    )
    whatsapp_from_phone = fields.Char()
    whatsapp_version = fields.Char(default="15.0")
