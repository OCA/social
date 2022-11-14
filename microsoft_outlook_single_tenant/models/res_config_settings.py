# Copyright 2022 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    microsoft_outlook_directory_tenant_id = fields.Char(
        string="Directory (tenant) ID",
        help="Place here Tenant ID (or Application ID), if single-tenant application",
        config_parameter="microsoft_outlook_directory_tenant_id",
    )
