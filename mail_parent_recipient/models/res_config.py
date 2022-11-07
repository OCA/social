# Copyright 2022 Camptocamp SA
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    use_parent_mail_address = fields.Boolean(
        config_parameter="mail.use_parent_address",
        help="""
            When checked, for partner without eamil the system will try
            to use the email address of the partner's parent.
        """,
    )
