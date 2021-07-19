# Copyright 2021 Hunki Enterprises BV
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


class MailActivityType(models.AbstractModel):
    _inherit = "mail.activity.type"

    predefined = fields.Boolean(
        default=False,
        help="Checking this box makes the activity a button "
        "users can click to add this activity to some record",
    )
    predefined_condition = fields.Text(
        string="Condition",
        help="Add python code to show this predefined type conditionally",
    )
