# Copyright 2024 CorporateHub
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


class IrModel(models.Model):
    _inherit = "ir.model"

    mail_post_access = fields.Selection(
        selection=[
            ("create", "Create"),
            ("read", "Read"),
            ("write", "Write"),
            ("unlink", "Delete"),
        ],
    )
