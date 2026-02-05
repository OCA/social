# Copyright 2026 Therp BV <https://therp.nl>.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

from odoo.tests.common import SavepointCase


class TestIrMailServer(SavepointCase):
    def test_compute_is_microsoft_outlook_configured(self):
        MailServer = self.env["ir.mail_server"]
        # Server not using outlook should not have outlook configured.
        example_server = MailServer.create(
            {
                "name": "Test Outlook Server",
                "smtp_host": "smtp.example.com",
                "smtp_port": 587,
                "smtp_encryption": "starttls",
                "smtp_user": "user1@example.com",
                "use_microsoft_outlook_service": False,
                "microsoft_outlook_client_identifier": False,
                "microsoft_outlook_client_secret": False,
            }
        )
        self.assertFalse(example_server.is_microsoft_outlook_configured)
        self.assertFalse(example_server.microsoft_outlook_uri)
        # Now test an outlook server, with client id and secret on the server record.
        outlook_server = MailServer.create(
            {
                "name": "Test Outlook Server",
                "smtp_host": "smtp.outlook.com",
                "smtp_port": 587,
                "smtp_encryption": "starttls",
                "smtp_user": "user1@somemail.com",
                "use_microsoft_outlook_service": True,
                "microsoft_outlook_client_identifier": "test_client_id",
                "microsoft_outlook_client_secret": "test_secret",
            }
        )
        self.assertTrue(outlook_server.is_microsoft_outlook_configured)
        self.assertIn(
            outlook_server.microsoft_outlook_client_identifier,
            outlook_server.microsoft_outlook_uri,
        )
