# Copyright 2022 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

from odoo.tests.common import TransactionCase


class TestFetchMailServerMicrosoftOutlook(TransactionCase):
    def _create_mail_server(self):
        return self.env["fetchmail.server"].create(
            {
                "name": "Test server",
                "use_microsoft_outlook_service": True,
                "user": "test@example.com",
                "password": "",
                "server_type": "imap",
                "is_ssl": True,
            }
        )

    def test_default_app_endpoint(self):
        self.env["res.config.settings"].create(
            {
                "microsoft_outlook_client_identifier": "test_client_id",
                "microsoft_outlook_client_secret": "test_secret",
            }
        ).set_values()

        mail_server = self._create_mail_server()
        common_endpoint = "https://login.microsoftonline.com/common/oauth2/v2.0/"
        self.assertIn(common_endpoint, mail_server.microsoft_outlook_uri)

    def test_single_tenant_app_endpoint(self):
        self.env["res.config.settings"].create(
            {
                "microsoft_outlook_client_identifier": "test_client_id",
                "microsoft_outlook_directory_tenant_id": "test_directory_tenant_id",
                "microsoft_outlook_client_secret": "test_secret",
            }
        ).set_values()

        mail_server = self._create_mail_server()
        mail_server = self.env["fetchmail.server"].create(
            {
                "name": "Test server",
                "use_microsoft_outlook_service": True,
                "user": "test@example.com",
                "password": "",
                "server_type": "imap",
                "is_ssl": True,
            }
        )

        single_tenant_endpoint = (
            "https://login.microsoftonline.com/test_directory_tenant_id/oauth2/v2.0/"
        )
        self.assertIn(single_tenant_endpoint, mail_server.microsoft_outlook_uri)
