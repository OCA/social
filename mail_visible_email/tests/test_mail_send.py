# Copyright 2025 Therp BV <https://therp.nl>.
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from odoo.tests import tagged

from odoo.addons.mail.tests.common import MailCommon


@tagged("-at_install", "post_install")
class TestMailSend(MailCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner = cls.env.ref("base.res_partner_address_31")
        cls.partner_cc = cls.env.ref("base.partner_demo")
        cls.partner_bcc = cls.env.ref("base.res_partner_main1")
        cls.mail_template = cls._create_template(
            "res.partner",
            template_values={
                "auto_delete": False,
                "email_to": cls.partner.email,
                "email_cc": cls.partner_cc.email,
            },
        )

    def test_email_to_cc_via_template(self):
        """Sending via template populates email_to and email_cc on mail.message."""
        Mail = self.env["mail.mail"]
        mail_id = self.mail_template.send_mail(self.partner.id, force_send=True)
        self.assertTrue(mail_id)
        mail = Mail.browse(mail_id)
        message = mail.mail_message_id
        self.assertTrue(message)
        self.assertEqual(message.email_to, self.partner.email)
        self.assertEqual(message.email_cc, self.partner_cc.email)

    def test_email_bcc_direct(self):
        """Setting email_bcc directly on mail.mail propagates to mail.message."""
        mail = self.env["mail.mail"].create(
            {
                "subject": "Test BCC",
                "body_html": "<p>Hello</p>",
                "email_to": self.partner.email,
                "email_bcc": self.partner_bcc.email,
                "state": "outgoing",
                "auto_delete": False,
            }
        )
        with self.mock_mail_gateway():
            mail._send()
        self.assertEqual(mail.mail_message_id.email_bcc, self.partner_bcc.email)
