# -*- coding: utf-8 -*-
# Copyright 2026 nurefexc (https://nurefexc.com)
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).

from odoo import fields, models

class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    ntfy_server_url = fields.Char(
        string="ntfy Server URL",
        help="The base URL of the ntfy server (e.g., https://ntfy.sh)",
        config_parameter="ntfy.server_url",
        default="https://ntfy.sh",
    )
