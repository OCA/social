# Copyright 2025 Therp BV <https://therp.nl>.
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


class MailMessage(models.Model):
    _inherit = "mail.message"

    email_to = fields.Char(
        string="To",
        readonly=True,
        help="original email addresses in 'to' header",
    )
    email_cc = fields.Char(
        string="Cc",
        readonly=True,
        help="original email addresses in 'cc' header",
    )
    email_bcc = fields.Char(
        string="Bcc",
        readonly=True,
        help="original email addresses in 'bcc' header",
    )
