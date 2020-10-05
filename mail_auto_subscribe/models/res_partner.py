# Copyright 2020 ADHOC SA
#   Nicolás Messina <nm@adhoc.com.ar>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import fields, models


class ResPartnerCategory(models.Model):
    _inherit = "res.partner.category"

    auto_subscribe = fields.Boolean(string="Auto-subscribe")
    model_ids = fields.Many2many(comodel_name="ir.model", string="Models")

    def name_get(self):
        result = []
        for tag in self:
            if tag.auto_subscribe:
                name = tag.name + " - \u24B6\u24C8"
            else:
                name = tag.name
            result.append((tag.id, name))
        return result
