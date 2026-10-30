# Copyright 2025 Quartile (https://www.quartile.co)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


class EmailLayoutMapping(models.Model):
    _name = "email.layout.mapping"
    _description = "Email Layout Mapping"

    layout_id = fields.Many2one("ir.ui.view", ondelete="cascade")
    substitute_layout_id = fields.Many2one(
        "ir.ui.view",
        domain=[("type", "=", "qweb")],
        required=True,
        help="Select a target layout.",
    )
    model_ids = fields.Many2many(
        "ir.model", string="Models", help="Select models that the swapping applies to."
    )
