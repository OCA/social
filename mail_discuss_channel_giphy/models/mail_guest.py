# Copyright 2026 Bernat Obrador APSL-Nagarro
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import models


class MailGuest(models.Model):
    _inherit = "mail.guest"

    def _init_messaging(self):
        res = super()._init_messaging()
        res["hasGifPickerFeature"] = bool(
            self.env["ir.config_parameter"].sudo().get_param("discuss.giphy_api_key")
        )
        return res
