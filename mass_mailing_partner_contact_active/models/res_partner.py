# Copyright 2022 Camptocamp SA
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl)
from odoo import models


class ResPartner(models.Model):

    _inherit = "res.partner"

    def write(self, values):
        res = super().write(values)
        if "active" in values:
            self.env["mailing.contact"].with_context(active_test=False).sudo().search(
                [("partner_id", "in", self.ids)]
            ).write({"active": values["active"]})
        return res
