# Copyright 2020 Tecnativa - Alexandre Díaz
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import api, models


class IrConfigParameter(models.Model):
    _inherit = "ir.config_parameter"

    @api.model_create_multi
    def create(self, vals_list):
        res = super().create(vals_list)
        self.env["mail.alias"].clear_caches()
        return res

    def write(self, vals):
        res = super().write(vals)
        self.env["mail.alias"].clear_caches()
        return res

    def unlink(self):
        res = super().unlink()
        self.env["mail.alias"].clear_caches()
        return res
