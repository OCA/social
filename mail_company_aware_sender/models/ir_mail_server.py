# Copyright 2025 Therp BV <https://therp.nl>.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import _, api, models
from odoo.exceptions import ValidationError
from odoo.tools import email_domain_extract


class IrMailServer(models.Model):

    _inherit = "ir.mail_server"

    @api.model
    def _is_domain_whitelisted(self, domain):
        """Check whether domain has been whitelisted for sending."""
        whitelist_servers = self.search([]).filtered("domain_whitelist")
        for server in whitelist_servers:
            if domain in self._get_domain_whitelist(server.domain_whitelist):
                return True
        return False

    def _get_test_email_addresses(self):
        self.ensure_one()
        if self.from_filter or not self.env.user.email:
            return super()._get_test_email_addresses()
        email_to = "noreply@odoo.com"
        email_from = self.env.user.company_aware_email()
        email_domain = email_domain_extract(email_from)
        valid_domains = self._get_domain_whitelist(self.domain_whitelist)
        if email_domain not in valid_domains:
            raise ValidationError(
                _(
                    "Domain %s not whitelisted on this server",
                    email_domain,
                )
            )
        return email_from, email_to

    @api.model
    def _get_default_from_address(self):
        """Prevent overwrite of email_from."""
        return None
