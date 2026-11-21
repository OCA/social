# Copyright 2026 Binhex
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import re

from odoo import api, models
from odoo.exceptions import UserError

from odoo.addons.phone_validation.tools import phone_validation


def normalize_phone(number, country=None):
    """The digits of a phone in international format, as WhatsApp sends them.

    WhatsApp identifies a sender by its number with the country code and
    without "+" (e.g. 34600000000). A number written without international
    prefix is completed with the code of ``country``.
    """
    number = (number or "").strip()
    if not number:
        return ""
    if not number.startswith(("+", "00")) and country:
        try:
            number = phone_validation.phone_format(
                number,
                country.code,
                country.phone_code,
                force_format="E164",
                raise_exception=True,
            )
        except UserError:
            # Not a valid national number: keep the digits as written.
            number = (number or "").strip()
    digits = re.sub(r"\D", "", number)
    return digits[2:] if number.startswith("00") else digits


class MailMessageImportAddress(models.Model):
    """The WhatsApp addresses are phones."""

    _inherit = "mail.message.import.address"

    @api.model
    def _normalize_address(self, channel_type, address, company):
        if channel_type != "whatsapp":
            return super()._normalize_address(channel_type, address, company)
        digits = normalize_phone(address, company.country_id)
        return digits if 8 <= len(digits) <= 15 else ""

    def _invalid_address_message(self):
        if self.channel_type != "whatsapp":
            return super()._invalid_address_message()
        return self.env._(
            "The phone %(phone)s is not valid: write it in international format, "
            "e.g. +34 600 000 000.",
            phone=self.address,
        )
