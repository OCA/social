# Copyright 2021 Camptocamp (http://www.camptocamp.com).
# @author Iván Todorovich <ivan.todorovich@gmail.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class MailingContact(models.Model):
    _inherit = "mailing.contact"

    email = fields.Char(copy=False)

    _sql_constraints = [
        (
            "unique_email",
            "UNIQUE(email_normalized)",
            "There's already a contact with this email address",
        )
    ]
