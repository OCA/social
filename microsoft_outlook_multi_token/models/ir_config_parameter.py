# Copyright 2025 Hunki Enterprises BV
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl-3.0)

from odoo import api, models


class IrConfigParameter(models.Model):
    _inherit = "ir.config_parameter"

    @api.model
    def get_param(self, key, default=False):
        multi_token_record = self.env.context.get("microsoft_outlook_multi_token")
        if (
            key in ("microsoft_outlook_client_id", "microsoft_outlook_client_secret")
            and isinstance(multi_token_record, models.Model)
            and multi_token_record.sudo()[key]
        ):
            return multi_token_record.sudo()[key]
        return super().get_param(key, default=default)
