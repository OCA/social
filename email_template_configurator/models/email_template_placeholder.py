# Copyright 2018 ACSONE SA/NV
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class EmailTemplatePlaceholder(models.Model):

    _name = "email.template.placeholder"
    _description = "Email Template Placeholder"

    name = fields.Char(
        required=True,
    )
    model_id = fields.Many2one(
        comodel_name="ir.model",
        string="Model",
        required=True,
        ondelete="cascade",
    )
    placeholder = fields.Char(
        required=True,
        default="${object.}",
    )
    active = fields.Boolean(
        default=True,
    )
