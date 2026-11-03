# Copyright 2026 Binhex
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import _, api, models
from odoo.tools import email_normalize


class MailMessageImportAddress(models.Model):
    """The email addresses are compared normalized."""

    _inherit = "mail.message.import.address"

    @api.model
    def _normalize_address(self, channel_type, address, company):
        if channel_type != "email":
            return super()._normalize_address(channel_type, address, company)
        return email_normalize(address or "") or ""

    def _invalid_address_message(self):
        if self.channel_type != "email":
            return super()._invalid_address_message()
        return _(
            "The address %(email)s is not a valid email address.", email=self.address
        )
