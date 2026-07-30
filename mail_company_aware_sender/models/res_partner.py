# Copyright 2025 Therp BV <https://therp.nl>.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import fields, models
from odoo.tools import formataddr


class ResPartner(models.Model):
    _inherit = "res.partner"

    fixed_email = fields.Boolean(
        help="Email for partner will not be influenced by company",
    )

    def company_aware_email(self, company=None, default_email=None):
        """Set email using company email domain if configured."""
        self.ensure_one()
        result_email = default_email or self.email
        if not self.fixed_email:
            company = company or self.env.company
            if company._override_email_domain():
                before_at = self.email.split("@")[0]
                after_at = company.email.split("@")[1]
                result_email = f"{before_at}@{after_at}"
                if company.format_email:
                    # formataddr wants a tuple with name (or False) and email.
                    result_email = formataddr((self.name, result_email))
        return result_email
