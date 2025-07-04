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
