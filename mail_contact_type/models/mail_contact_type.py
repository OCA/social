# Copyright 2023 Foodles (https://www.foodles.com/)
# @author Pierre Verkest <pierreverkest84@gmail.com>
# @author Matthias Barkat <matthias.barkat@foodles.co>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
from odoo import fields, models


class MailContactType(models.Model):
    _name = "mail.contact.type"
    _description = "Mail Contact Type"

    _sql_constraints = [
        ("code_uniq", "unique (code)", "The code must be unique"),
    ]

    name = fields.Char(required=True, translate=True)
    code = fields.Char(required=True)
