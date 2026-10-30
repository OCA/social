# Copyright 2024 Tecnativa - David Vidal
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from odoo import api, fields, models


class MailingSubscription(models.Model):
    _inherit = "mailing.subscription"

    metadata = fields.Text()

    @api.model_create_multi
    def create(self, vals_list):
        if self.env.context.get("metadata"):
            for vals in vals_list:
                vals["metadata"] = self.env.context.get("metadata")
        return super().create(vals_list)

    def write(self, vals):
        if self.env.context.get("metadata"):
            vals["metadata"] = self.env.context.get("metadata")
        return super().write(vals)
