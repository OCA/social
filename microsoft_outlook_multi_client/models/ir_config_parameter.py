# Copyright 2026 Therp BV <https://therp.nl>.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
"""Patch get_param for microsoft client_id and client_secret.

To avoid having to re-implement a lot of the standard functions that assume
client_id and client_secret are defined in ir.config_parameter, we will patch get_param
to return these values if they have already been set in the context.

Actually we will do this in a way that might have broader application, but for now we
will fill those with the values in ir.mail_server if set.
"""
from odoo import api, models


class IrConfigParameter(models.Model):
    _inherit = "ir.config_parameter"

    @api.model
    def get_param(self, key, default=False):
        """Retrieve the value for a given key.

        Override to return value from context, if set there. This is to help
        modules to override functions that expect a value from a system parameter
        but already have the value set in some other way.
        """
        preset_key = f"preset_{key}"
        preset_value = self.env.context.get(preset_key, False)
        if preset_value:
            return preset_value
        return super().get_param(key, default=default)
