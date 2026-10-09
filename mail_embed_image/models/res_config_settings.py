# Copyright 2024 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    image_embedding_method = fields.Selection(
        related="company_id.image_embedding_method",
        readonly=False,
    )
