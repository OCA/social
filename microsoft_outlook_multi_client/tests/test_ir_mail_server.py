# Copyright 2026 Therp BV <https://therp.nl>.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)
from mock import MagicMock, patch

from odoo.tests.common import SavepointCase

OUTLOOK_MIXIN = "odoo.addons.microsoft_outlook.models.microsoft_outlook_mixin"


class TestIrMailServer(SavepointCase):
    @classmethod
    def setUpClass(cls):
        super(TestIrMailServer, cls).setUpClass()
        cls.MailServer = cls.env["ir.mail_server"]
        cls.outlook_server = cls.MailServer.create(
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

    def test_multi_outlook_configured(self):
        # Now test the outlook server, with client id and secret on the server record.
        self.assertTrue(self.outlook_server.is_microsoft_outlook_configured)
        self.assertIn(
            self.outlook_server.microsoft_outlook_client_identifier,
            self.outlook_server.microsoft_outlook_uri,
        )

    def test_outlook_not_configured(self):
        # Server not using outlook should not have outlook configured.
        example_server = self.MailServer.create(
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

    def test_system_outlook_configured(self):
        # Now test an outlook server, getting client id and secret from system parms.
        self.env["res.config.settings"].create(
            {
                "microsoft_outlook_client_identifier": "test_system_client_id",
                "microsoft_outlook_client_secret": "test_system_secret",
            }
        ).set_values()
        system_outlook_server = self.MailServer.create(
            {
                "name": "Test System Outlook Server",
                "smtp_host": "smtp.outlook.com",
                "smtp_port": 587,
                "smtp_encryption": "starttls",
                "smtp_user": "user1@example.com",
                "use_microsoft_outlook_service": True,
                "microsoft_outlook_client_identifier": False,
                "microsoft_outlook_client_secret": False,
            }
        )
        self.assertTrue(system_outlook_server.is_microsoft_outlook_configured)
        self.assertIn(
            "test_system_client_id",
            system_outlook_server.microsoft_outlook_uri,
        )

    @patch(OUTLOOK_MIXIN + ".requests")
    def test_fetch_outlook_refresh_token(self, mock_request):
        # mock the response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "refresh_token": "abc",
            "access_token": "xyz",
            "expires_in": 90,
        }
        mock_request.post.return_value = mock_response
        result = self.outlook_server._fetch_outlook_refresh_token("dummy_code")
        self.assertEqual(result[0], "abc")
