# Copyright 2023 Camptocamp
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


class Company(models.Model):
    _inherit = "res.company"

    default_partner_cc_ids = fields.Many2many(
        "res.partner",
        "res_company_res_partner_cc_rel",
        "company_id",
        "partner_id",
        string="Default Cc",
    )
    default_partner_bcc_ids = fields.Many2many(
        "res.partner",
        "res_company_res_partner_bcc_rel",
        "company_id",
        "partner_id",
        string="Default Bcc",
    )
