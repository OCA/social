# Copyright 2024 Dixmit
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class MailGuest(models.Model):
    _inherit = "mail.guest"

    broker_id = fields.Many2one("mail.broker")
    broker_token = fields.Char()

    def _guest_format(self, fields=None):
        result = super()._guest_format(fields=fields)
        if not fields or fields.get("broker_id"):
            for guest in result:
                result[guest]["broker_id"] = guest.broker_id.id
        return result
