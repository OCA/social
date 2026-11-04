# Copyright 2025 Quartile
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    mail_domain_blacklist = fields.Char(
        config_parameter="iap_mail_domain_blacklist.mail_domain_blacklist"
    )
