# Copyright 2024 Dixmit
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class MailGuest(models.Model):
    _inherit = "mail.guest"

    gateway_id = fields.Many2one("mail.gateway")
    gateway_token = fields.Char()

    def _guest_format(self, fields=None):
        result = super()._guest_format(fields=fields)
        if not fields or "gateway_id" in fields:
            for guest in result:
                result[guest]["gateway"] = {"id": guest.gateway_id.id}
        return result
