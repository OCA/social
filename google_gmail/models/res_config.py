# Copyright 2022 Camptocamp SA
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

from odoo import api, fields, models


class BaseConfigSettings(models.TransientModel):
    _inherit = "base.config.settings"

    google_gmail_client_identifier = fields.Char("Gmail Client Id")
    google_gmail_client_secret = fields.Char("Gmail Client Secret")

    @api.multi
    def set_gmail_client_identifier(self):
        google_gmail_client_identifier = self.google_gmail_client_identifier or ""
        self.env["ir.config_parameter"].set_param(
            "google_gmail_client_identifier",
            google_gmail_client_identifier,
            groups=["base.group_system"],
        )

    @api.multi
    def set_gmail_client_secret(self):
        google_gmail_client_secret = self.google_gmail_client_secret or ""
        self.env["ir.config_parameter"].set_param(
            "google_gmail_client_secret",
            google_gmail_client_secret,
            groups=["base.group_system"],
        )

    @api.multi
    def get_default_gmail_credentials(self, fields=None):
        get_param = self.env["ir.config_parameter"].sudo().get_param
        google_gmail_client_identifier = get_param(
            "google_gmail_client_identifier", default=""
        )
        google_gmail_client_secret = get_param("google_gmail_client_secret", default="")
        return {
            "google_gmail_client_identifier": google_gmail_client_identifier,
            "google_gmail_client_secret": google_gmail_client_secret,
        }
