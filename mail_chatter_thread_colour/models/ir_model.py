# Copyright 2022 CreuBlanca
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


class IrModel(models.Model):

    _inherit = "ir.model"

    thread_colour = fields.Char()
    thread_font_colour = fields.Char()
