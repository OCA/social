# Copyright 2025 Therp BV <https://therp.nl>.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
from odoo.exceptions import ValidationError

from .common import CompanyAwareSenderCase


class TestMailServer(CompanyAwareSenderCase):
    def test_test_email_adresses(self):
        # Whitelist domain, and enable from address.
        self.mail_server.write(
            {
                "from_filter": "info@therp.nl",
                "domain_whitelist": "therp.nl,kingdom.fr,imperiumromanum.org",
            }
        )
        email_from, email_to = self.mail_server._get_test_email_addresses()
        self.assertEqual(email_from, "info@therp.nl")
        self.assertEqual(email_to, "noreply@odoo.com")
        # Disable from_filter and remove therp.nl from whitelist.
        self.mail_server.write(
            {
                "from_filter": "info@therp.nl",
                "domain_whitelist": "kingdom.fr,imperiumromanum.org",
            }
        )
        self.mail_server.write({"from_filter": False})
        # Partner charles in imperium should use company aware from.
        email_from, email_to = (
            self.mail_server.with_user(self.user_charles)
            .with_company(self.company_imperium)
            ._get_test_email_addresses()
        )
        self.assertEqual(email_from, "charlemagne@imperiumromanum.org")
        self.assertEqual(email_to, "noreply@odoo.com")
        # There should be an exception when using an invalid email domain.
        self.company_imperium.write({"email": "court@aachen.de"})
        with self.assertRaises(ValidationError):
            self.mail_server.with_user(self.user_charles).with_company(
                self.company_imperium
            )._get_test_email_addresses()

    def test_disable_encapsulation(self):
        email_from = self.mail_server.with_company(
            self.company_imperium
        )._get_default_from_address()
        self.assertEqual(email_from, None)
