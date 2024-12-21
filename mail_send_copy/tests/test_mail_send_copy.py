# Copyright from 2024: Alwinen GmbH (https://www.alwinen.de)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

# TODO: find a way to test sending email with existing BCC

from unittest.mock import patch

from odoo.tests import tagged

from odoo.addons.mail.tests.test_mail_composer import TestMailComposer


class TestMailSendCopy(TestMailComposer):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context={"testing": True})

        # Create test partner
        cls.partner = cls.env["res.partner"].create(
            {
                "name": "Test Partner",
                "email": "test@example.com",
            }
        )

    def test_send_email_with_copy(self):
        """Test that sender is added to BCC when sending email"""
        composer = self.env["mail.compose.message"].create(
            {
                "partner_ids": [(6, 0, [self.partner.id])],
                "subject": "Test Subject",
                "body": "<p>Test Body</p>",
                "email_from": "sender@example.com",
            }
        )

        # Mock the send_email method
        with patch(
            "odoo.addons.base.models.ir_mail_server.IrMailServer.send_email"
        ) as mock_send_email:
            composer._action_send_mail()
            # Verify that send_email was called
            self.assertTrue(mock_send_email.called)
            # Get the arguments passed to send_email
            call_args = mock_send_email.call_args[0]
            # The message is the first argument
            message = call_args[0]
            # Check BCC in the email message
            self.assertIn("sender@example.com", message["Bcc"])

    def test_send_email_without_copy(self):
        """Test that sender is not added to BCC when do_not_send_copy is True"""
        composer = (
            self.env["mail.compose.message"]
            .with_context(do_not_send_copy=True)
            .create(
                {
                    "partner_ids": [(6, 0, [self.partner.id])],
                    "subject": "Test Subject No Copy",
                    "body": "<p>Test Body</p>",
                    "email_from": "sender@example.com",
                }
            )
        )

        with patch(
            "odoo.addons.base.models.ir_mail_server.IrMailServer.send_email"
        ) as mock_send_email:
            composer._action_send_mail()
            self.assertTrue(mock_send_email.called)
            message = mock_send_email.call_args[0][0]
            self.assertNotIn("Bcc", message)


# Code contributed by @trisdoan
@tagged("post_install", "-at_install")
class TestMailSendWithBcc(TestMailSendCopy):
    def test_send_email_with_existing_bcc(self):
        if not self.env["ir.module.module"].search(
            [("name", "=", "mail_composer_cc_bcc"), ("state", "=", "installed")]
        ):
            self.skipTest("mail_composer_cc_bcc module is required for this test")

        partner_bcc = self.env.ref("base.res_partner_main2")
        composer = self.env["mail.compose.message"].create(
            {
                "partner_ids": [(6, 0, [self.partner.id])],
                "subject": "Test Subject",
                "body": "<p>Test Body</p>",
                "email_from": "sender@example.com",
            }
        )
        composer.partner_bcc_ids = partner_bcc

        with patch(
            "odoo.addons.base.models.ir_mail_server.IrMailServer.send_email"
        ) as mock_send_email:
            composer._action_send_mail()
            # Verify that send_email was called
            self.assertTrue(mock_send_email.called)
            call_args = mock_send_email.call_args[0]
            message = call_args[0]
            # Check existing BCC in the email message
            self.assertIn("dwayne.newman28@example.com", message["Bcc"])
