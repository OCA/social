# Copyright from 2024: Alwinen GmbH (https://www.alwinen.de)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from email.message import EmailMessage

from odoo import Command

from odoo.addons.mail.tests.common import MailCommon


class TestMailSendCopyCommon(MailCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))
        cls.partner = cls.env["res.partner"].create(
            {
                "name": "Test Partner",
                "email": "test@example.com",
            }
        )

    def _send_composer_mail(self, email_from="sender@example.com", **context):
        composer = (
            self.env["mail.compose.message"]
            .with_context(**context)
            .create(
                {
                    "model": "res.partner",
                    "res_ids": [self.partner.id],
                    "partner_ids": [Command.set(self.partner.ids)],
                    "subject": "Test Subject",
                    "body": "<p>Test Body</p>",
                    "email_from": email_from,
                    "composition_mode": "comment",
                }
            )
        )
        with self.mock_mail_gateway():
            composer._action_send_mail()
        return self.emails

    def _send_message(self, message, **context):
        with self.mock_smtplib_connection():
            self.env["ir.mail_server"].with_context(**context).send_email(message)
        return self.emails


class TestMailSendCopy(TestMailSendCopyCommon):
    def test_send_email_with_copy(self):
        """The sender receives a copy of the email."""
        emails = self._send_composer_mail()
        self.assertEqual(len(emails), 1)
        self.assertCountEqual(
            emails[0]["smtp_to_list"], ["test@example.com", "sender@example.com"]
        )

    def test_send_email_without_copy(self):
        """The sender gets no copy when ``do_not_send_copy`` is set."""
        emails = self._send_composer_mail(do_not_send_copy=True)
        self.assertEqual(len(emails), 1)
        self.assertEqual(emails[0]["smtp_to_list"], ["test@example.com"])

    def test_send_email_with_existing_bcc(self):
        """The sender is added to the existing Bcc recipients."""
        message = EmailMessage()
        message["From"] = "sender@example.com"
        message["To"] = "test@example.com"
        message["Bcc"] = "existing@example.com"
        emails = self._send_message(message)
        self.assertCountEqual(
            emails[0]["smtp_to_list"],
            ["test@example.com", "existing@example.com", "sender@example.com"],
        )

    def test_send_email_with_formatted_sender(self):
        emails = self._send_composer_mail(email_from='"Bike@Home" <Sender@Example.com>')
        self.assertCountEqual(
            emails[0]["smtp_to_list"], ["test@example.com", "sender@example.com"]
        )

    def test_send_email_with_existing_bcc_and_validated_to(self):
        message = EmailMessage()
        message["From"] = "sender@example.com"
        message["To"] = "test@example.com"
        message["Bcc"] = "existing@example.com"
        emails = self._send_message(
            message, send_validated_to=["test@example.com", "existing@example.com"]
        )
        self.assertCountEqual(
            emails[0]["smtp_to_list"],
            ["test@example.com", "existing@example.com", "sender@example.com"],
        )

    def test_send_email_without_sender(self):
        """No copy is added when the email has no sender."""
        message = EmailMessage()
        message["To"] = "test@example.com"
        emails = self._send_message(message)
        self.assertEqual(emails[0]["smtp_to_list"], ["test@example.com"])
