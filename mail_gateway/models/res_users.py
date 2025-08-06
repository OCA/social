# Copyright 2024 Dixmit
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


class ResUsers(models.Model):
    _inherit = "res.users"

    gateway_ids = fields.Many2many("mail.gateway")

    def _init_messaging(self, store):
        result = super()._init_messaging(store)
        store.add({"gateways": self.gateway_ids.gateway_info()})
        return result
