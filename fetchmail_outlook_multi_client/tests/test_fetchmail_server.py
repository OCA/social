# Copyright 2026 Therp BV <https://therp.nl>.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)
from imaplib import IMAP4_SSL

from mock import MagicMock, patch

from odoo.tests.common import SavepointCase

OUTLOOK_MIXIN = "odoo.addons.microsoft_outlook.models.microsoft_outlook_mixin"


class TestFetchMailServer(SavepointCase):
    @classmethod
    def setUpClass(cls):
        super(TestFetchMailServer, cls).setUpClass()
        cls.MailServer = cls.env["fetchmail.server"]
        cls.outlook_server = cls.MailServer.create(
            {
                "name": "Test Fetchmail Outlook Server",
                "server": "imap.outlook.com",
                "port": 993,
                "server_type": "imap",
                "is_ssl": True,
                "user": "user1@somemail.com",
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
                "name": "Test Example Server",
                "server": "imap.example.com",
                "port": 993,
                "server_type": "imap",
                "is_ssl": True,
                "user": "user1@example.com",
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
                "server": "imap.example.com",
                "port": 993,
                "server_type": "imap",
                "is_ssl": True,
                "user": "user1@example.com",
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

    @patch(OUTLOOK_MIXIN + ".requests", spec=True)
    def test_imap_login(self, mock_request):
        # set refresh token, will lead to attempt to get fresh access token.
        self.outlook_server.write(
            {
                "microsoft_outlook_refresh_token": "fake_refresh_token",
            }
        )
        # mock the response, mock will be used to generate auth string for connection.
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "refresh_token": "abc",
            "access_token": "xyz",
            "expires_in": 90,
        }
        mock_request.post.return_value = mock_response
        connection = MagicMock(spec=IMAP4_SSL)
        self.outlook_server._imap_login(connection)
        connection.authenticate.assert_called_once()
        connection.select.assert_called_once()
