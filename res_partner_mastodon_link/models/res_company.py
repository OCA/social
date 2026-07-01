# Copyright (C) 2025 - Today: Sylvain LE GAL (http://www.grap.coop)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class Company(models.Model):
    _inherit = "res.company"

    # makes the module working correctly when res_company_mastodon_link
    # is installed
    social_mastodon = fields.Char(
        string="Mastodon Account", related="partner_id.social_mastodon", store=True
    )
