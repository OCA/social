# Copyright 2026 Bernat Obrador APSL-Nagarro
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    giphy_api_key = fields.Char(
        string="GIPHY API Key",
        config_parameter="discuss.giphy_api_key",
    )
    giphy_gif_limit = fields.Integer(
        default=8,
        config_parameter="discuss.giphy_gif_limit",
        help="Fetch up to the specified number of GIF.",
    )
    giphy_rating = fields.Selection(
        [("g", "G"), ("pg", "PG"), ("pg-13", "PG-13"), ("r", "R"), ("any", "Any")],
        config_parameter="discuss.giphy_rating",
        default="pg",
    )
