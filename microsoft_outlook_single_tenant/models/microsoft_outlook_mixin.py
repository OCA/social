# Copyright 2022 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

from odoo import models


class MicrosoftOutlookMixin(models.AbstractModel):
    _inherit = "microsoft.outlook.mixin"

    @property
    def _OUTLOOK_ENDPOINT(self):
        outlook_endpoint = "https://login.microsoftonline.com/{path}/oauth2/v2.0/"
        path = (
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("microsoft_outlook_directory_tenant_id", "common")
        )
        return outlook_endpoint.format(path=path)
