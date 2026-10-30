# Copyright 2024 Dixmit
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models

from odoo.addons.mail.tools.discuss import Store


class MailGuest(models.Model):
    _inherit = "mail.guest"

    gateway_id = fields.Many2one("mail.gateway")
    gateway_token = fields.Char()

    def _to_store(self, store: Store, /, *, fields=None):
        result = super()._to_store(store, fields=fields)
        if not fields or "gateway_id" in fields:
            for record in self:
                store.add(record, {"gateway": {"id": record.gateway_id.id}})
        return result
