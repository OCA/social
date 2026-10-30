# Copyright 2023 Camptocamp
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).


from odoo import fields, models


class MailTemplate(models.Model):
    _inherit = "mail.template"

    email_bcc = fields.Char(
        "Bcc", help="Blind cc recipients (placeholders may be used here)"
    )
