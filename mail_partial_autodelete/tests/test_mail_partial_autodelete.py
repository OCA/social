# Copyright 2021 Akretion (http://www.akretion.com)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo.tests.common import TransactionCase


class TestMailPartialAutodeleteCase(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.mail = cls.env["mail.mail"].create(
            {
                "subject": "Test subject",
                "body_html": "example body",
                "email_to": "test@example.com",
                "email_from": cls.env.user.email,
            }
        )

    def test_no_autodelete(self):
        self.mail.auto_delete = False
        self.mail._send()
        self.assertEqual(self.mail.body_html, "example body")

    def test_autodelete_only_purge(self):
        self.mail.auto_delete = True
        self.mail._send()
        self.assertEqual(self.mail.body_html, "")

    def test_autodelete_only_purge_debugmode(self):
        self.env["ir.config_parameter"].create(
            {"key": "mail_partial_autodelete_debugmode", "value": 1}
        )
        self.mail.auto_delete = True
        self.mail._send()
        self.assertEqual(self.mail.body_html, "example body")

    def test_autodelete_sent_kept(self):
        self.mail.auto_delete = True
        self.mail._send()
        self.assertTrue(self.mail.exists())
        self.assertEqual(self.mail.state, "sent")

    def test_autodelete_invalid_recipient_deleted(self):
        self.mail.write({"auto_delete": True, "email_to": "not-an-em"})
        self.mail._send()
        self.assertFalse(self.mail.exists())

    def test_autodelete_notification_body_kept(self):
        partner = self.env["res.partner"].create(
            {"name": "Partner", "email": "partner@example.com"}
        )
        message = partner.message_post(body="notification")
        self.mail.write(
            {
                "auto_delete": True,
                "mail_message_id": message.id,
                "is_notification": True,
            }
        )
        self.mail._send()
        self.assertTrue(self.mail.exists())
        self.assertEqual(self.mail.body_html, "example body")

    def test_explicit_unlink(self):
        self.mail.unlink()
        self.assertFalse(self.mail.exists())
