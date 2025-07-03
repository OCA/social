# Copyright 2025 Therp BV <https://therp.nl>.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import api, models


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
