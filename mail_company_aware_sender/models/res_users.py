# Copyright 2025 Therp BV <https://therp.nl>.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import models


class ResUsers(models.Model):
    _inherit = "res.users"

    def company_aware_email(self, company=None, default_email=None):
        """Set email using company email domain if configured."""
        self.ensure_one()
        return self.partner_id.company_aware_email(
            company=company, default_email=default_email
        )

    def get_company_aware_email(self, record):
        """Get company aware email_from related to Odoo record.

        Can be used on email_from field of template like so:
            {{ user.get_company_aware_email(object) }}
        """
        record.ensure_one()  # Must be recordlist with exactly one member.
        user = record.user_id if "user_id" in record._fields else self.env.user
        company = (
            record.company_id if "company_id" in record._fields else self.env.company
        )
        return user.company_aware_email(company=company)
