# Copyright 2025 Hunki Enterprises BV
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl-3.0)

from odoo.tests.common import Form, TransactionCase


class TestMicrosoftOutlookMultiToken(TransactionCase):
    def setUp(self):
        super().setUp()
        self.env["ir.config_parameter"].set_param("microsoft_outlook_client_id", False)
        self.env["ir.config_parameter"].set_param(
            "microsoft_outlook_client_secret", False
        )

    def test_microsoft_outlook_multi_token(self):
        """Test UI"""
        with Form(self.env["ir.mail_server"]) as mail_server_form:
            self.assertFalse(mail_server_form.is_microsoft_outlook_configured)
            mail_server_form.name = "test outlook server"
            mail_server_form.smtp_user = "test@test.com"
            mail_server_form.use_microsoft_outlook_service = True
            mail_server_form.microsoft_outlook_client_id = "hello"
            mail_server_form.microsoft_outlook_client_secret = "world"
            self.assertTrue(mail_server_form.is_microsoft_outlook_configured)
            mail_server = mail_server_form.save()

        self.assertIn("hello", mail_server.microsoft_outlook_uri)
