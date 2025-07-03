# Copyright 2025 Therp BV <https://therp.nl>.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import fields, models
from odoo.tools import email_domain_extract


class ResCompany(models.Model):
    _inherit = "res.company"

    use_email_domain = fields.Boolean(
        help="Use domain part of company for sender email address",
    )
    format_email = fields.Boolean(
        default=True,  # As this is what Odoo standard does.
        help='Format email_from with name "John Smith" <john.smith@example.com>'
        " or use plain email address",
    )

    def _override_email_domain(self):
        """Check whether company email domain can and should be used."""
        self.ensure_one()
        if not (self.use_email_domain and self.email):
            return False
        email_domain = email_domain_extract(self.email)
        return self.env["ir.mail_server"].sudo()._is_domain_whitelisted(email_domain)
