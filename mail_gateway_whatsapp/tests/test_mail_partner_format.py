# Copyright 2026 Creu Blanca
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from odoo.tests.common import TransactionCase, new_test_user


class TestMailPartnerFormat(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.gateway_user = new_test_user(
            cls.env,
            login="mail_gateway_format_test_gateway_user",
            groups="base.group_user,mail_gateway.gateway_user",
        )
        cls.regular_user = new_test_user(
            cls.env,
            login="mail_gateway_format_test_regular_user",
            groups="base.group_user",
        )
        cls.gateway = cls.env["mail.gateway"].create(
            {
                "name": "Test gateway",
                "gateway_type": "whatsapp",
                "token": "test-token",
            }
        )
        cls.partner = cls.env["res.partner"].create({"name": "Mentioned partner"})
        cls.env["res.partner.gateway.channel"].create(
            {
                "partner_id": cls.partner.id,
                "gateway_id": cls.gateway.id,
                "gateway_token": "test-channel-token",
            }
        )

    def test_mail_partner_format_gateway_user(self):
        """Users in the gateway_user group get the gateway channels info."""
        result = self.partner.with_user(self.gateway_user).mail_partner_format()
        self.assertIn("gateway_channels", result[self.partner])
        self.assertTrue(result[self.partner]["gateway_channels"])

    def test_mail_partner_format_regular_user(self):
        """Users outside the gateway_user group must not trigger an
        AccessError on res.partner.gateway.channel (e.g. when mentioning a
        partner with @ in the composer, which calls mail_partner_format)."""
        result = self.partner.with_user(self.regular_user).mail_partner_format()
        self.assertNotIn("gateway_channels", result[self.partner])
