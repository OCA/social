# Copyright 2018 Tecnativa - Ernesto Tejeda
# Copyright 2021 Camptocamp - Iván Todorovich
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import models


class MailingContact(models.Model):
    _inherit = "mailing.contact"

    _sql_constraints = [
        (
            "unique_email",
            "UNIQUE(email_normalized)",
            "There's already a contact with this email address",
        )
    ]
