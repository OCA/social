# Copyright 2021 ForgeFlow S.L.
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html).
from odoo import _, fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    opt_out = fields.Boolean(
        string="Opt Out",
        compute="_compute_opt_out",
        inverse="_inverse_opt_out",
        search="_search_opt_out",
        help="Setting this checkbox will add the partner's email to a "
        "blacklist so that this email won't be considered in mailings.",
    )

    def _compute_opt_out(self):
        blacklist = (
            self.env["mail.blacklist"]
            .sudo()
            .search([("email", "in", self.mapped("email"))])
        )
        blacklisted_emails = blacklist.mapped("email")
        for rec in self:
            if rec.email in blacklisted_emails:
                rec.opt_out = True
            else:
                rec.opt_out = False

    def _inverse_opt_out(self):
        for rec in self:
            if rec.opt_out and rec.email:
                self.env["mail.blacklist"].sudo()._add(self.email)
            elif not rec.opt_out and rec.email:
                self.env["mail.blacklist"].sudo()._remove(self.email)

    def _is_unsupported_search_operator(self, operator):
        return operator not in ["=", "!="]

    def _search_opt_out(self, operator, value):
        if self._is_unsupported_search_operator(operator):
            raise ValueError(_("Unsupported search operator"))
        blacklisted_emails = (
            self.env["mail.blacklist"].sudo().search([]).mapped("email")
        )
        if (operator == "=" and value) or (operator == "!=" and not value):
            search_operator = "in"
        else:
            search_operator = "not in"
        return [("email", search_operator, blacklisted_emails)]
