# Copyright 2025-2026 Therp BV <https://therp.nl>.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo.exceptions import ValidationError

from .common import CompanyAwareSenderCase


class TestMailServer(CompanyAwareSenderCase):
    def test_test_email_adresses(self):
        # Whitelist domain, and enable from address.
        self.mail_server.write(
            {
                "smtp_from": "info@therp.nl",
                "domain_whitelist": "therp.nl,kingdom.fr,imperiumromanum.org",
            }
        )
        email_from, email_to = self.mail_server._get_test_email_addresses()
        self.assertEqual(email_from, "info@therp.nl")
        self.assertEqual(email_to, "noreply@odoo.com")
        # Disable smtp_from and remove therp.nl from whitelist.
        self.mail_server.write(
            {
                "smtp_from": "info@therp.nl",
                "domain_whitelist": "kingdom.fr,imperiumromanum.org",
            }
        )
        self.mail_server.write({"smtp_from": False})
        # Partner charles in imperium should use company aware from.
        email_from, email_to = (
            self.mail_server.with_user(self.user_charles)
            .with_company(self.company_imperium)
            ._get_test_email_addresses()
        )
        self._assert_email(email_from, "charlemagne@imperiumromanum.org")
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

    def test_email_server_selection(self):
        # When one server has domain whitelisted, that server should send message.
        self.IrMailServer.create(
            {
                "name": "default mail server",
                "smtp_host": "localhost",
                "domain_whitelist": "therp.nl",
                "sequence": 5,
            }
        )
        # First test with smtp_from.
        self.mail_server.write(
            {
                "smtp_from": "info@imperiumromanum.org",
                "domain_whitelist": "imperiumromanum.org",
            }
        )
        # Partner charles in imperium should use company aware from.
        email_from, email_to = (
            self.mail_server.with_user(self.user_charles)
            .with_company(self.company_imperium)
            ._get_test_email_addresses()
        )
        self._assert_email(email_from, "info@imperiumromanum.org")
        # Call the (misspelled) _get_mail_sever method, defined in the
        # mail_outbound_static module, to select the right mail server.
        mail_server_id = self.IrMailServer._get_mail_sever("imperiumromanum.org")
        # The server with the domain should be used, despite higher sequence.
        self.assertEqual(mail_server_id, self.mail_server.id)
        # Now test with no smtp_from.
        self.mail_server.write({"smtp_from": False})
        email_from, email_to = (
            self.mail_server.with_user(self.user_charles)
            .with_company(self.company_imperium)
            ._get_test_email_addresses()
        )
        self._assert_email(email_from, "charlemagne@imperiumromanum.org")
        mail_server_id = self.IrMailServer._get_mail_sever("imperiumromanum.org")
        self.assertEqual(mail_server_id, self.mail_server.id)
