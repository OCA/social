# Copyright 2023 Camptocamp SA
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).


from odoo import _, fields, models, tools


def format_emails(partners):
    emails = [
        tools.formataddr((p.name or "False", p.email or "False")) for p in partners
    ]
    return ", ".join(emails)


class MailMail(models.Model):
    _inherit = "mail.mail"

    email_bcc = fields.Char("Bcc", help="Blind Cc message recipients")