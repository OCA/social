# -*- coding: utf-8 -*-
# Copyright 2022 Camptocamp SA
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

from odoo import fields, models


class BaseConfiguration(models.TransientModel):
    _inherit = "base.config.settings"

    use_parent_mail_address = fields.Boolean(
        related="company_id.use_parent_mail_address",
        help="""
            When checked, for partner without eamil the system will try
            to use the email address of the partner's parent.
        """
    )
