# Copyright 2022 CreuBlanca
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    thread_colour = fields.Char(
        string="Define base colour for model threads",
        config_parameter="mail_chatter.base_colour",
    )
    thread_font_colour = fields.Char(
        string="Define base font colour for model threads",
        config_parameter="mail_chatter.base_font_colour",
    )
