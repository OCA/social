# Copyright 2017 Tecnativa - Pedro M. Baeza
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import models


class ResPartner(models.Model):
    _inherit = "res.partner"

    def write(self, vals):
        """Allow to write values in mass mailing contact."""
        return super(ResPartner, self.with_context(syncing=True)).write(vals)
