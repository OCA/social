# Copyright 2025 Quartile (https://www.quartile.co)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


class IrUiView(models.Model):
    _inherit = "ir.ui.view"

    layout_mapping_line_ids = fields.One2many("email.layout.mapping", "layout_id")
