# Copyright 2025 Therp BV <https://therp.nl>.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
from odoo import models


class MailThread(models.AbstractModel):
    _inherit = "mail.thread"

    def _message_compute_author(self, author_id, email_from, raise_exception=True):
        """Set email from using company email domain.

        We will NOT override an explicitly passed email_from.

        Check for current company to see whether we should try to override
        the email_from domain.
        """
        email_passed = bool(email_from)
        author_id, email_from = super()._message_compute_author(
            author_id, email_from, raise_exception=raise_exception
        )
        if (not email_passed) and author_id:
            author = self.env["res.partner"].browse(author_id)
            email_from = author.company_aware_email(default_email=email_from)
        return author_id, email_from
