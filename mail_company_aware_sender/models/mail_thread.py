# Copyright 2025 Therp BV <https://therp.nl>.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
from odoo import models
from odoo.tools import formataddr


class MailThread(models.AbstractModel):
    _inherit = "mail.thread"

    def _message_compute_author(self, author_id, email_from, raise_on_email=True):
        """Set email from using company email domain.

        We will NOT override an explicitly passed email_from.

        Check for current company to see whether we should try to override
        the email_from domain.
        """
        override_from = (not email_from) and self.env.company._override_email_domain()
        author_id, email_from = super()._message_compute_author(
            author_id, email_from, raise_on_email=raise_on_email
        )
        if override_from and author_id:
            author = self.env["res.partner"].browse(author_id)
            before_at = author.email.split("@")[0]
            after_at = self.env.company.email.split("@")[1]
            email_from = f"{before_at}@{after_at}"
            if self.env.company.format_email:
                # formataddr wants a tuple with name (of False) and email.
                email_from = formataddr((author.name, email_from))
        return author_id, email_from
