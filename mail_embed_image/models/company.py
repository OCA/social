# Copyright 2024 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    image_embedding_method = fields.Selection(
        selection=[
            ("none", "No postprocessing"),
            ("cid", "Content-ID (Gmail, Office compatible)"),
            ("data", "HTML Inline Data"),
        ],
        default="cid",
        required=True,
    )
