# Copyright 2025 Therp BV <https://therp.nl>.
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from odoo.tests import Form

from odoo.addons.mail.tests.test_mail_composer import TestMailComposer


class TestMailSend(TestMailComposer):
    @classmethod
    def setUpClass(cls):
        # Based on example in mail_composer_cc_bcc.
        super().setUpClass()
        env = cls.env
        cls.partner = env.ref("base.res_partner_address_31")
        cls.partner_cc = env.ref("base.partner_demo")
        cls.partner_cc2 = env.ref("base.partner_demo_portal")
        cls.partner_bcc = env.ref("base.res_partner_main1")
        cls.mail_template = cls._create_template(
            "res.partner",
            template_values={
                "auto_delete": False,
                "email_to": cls.partner.email,
                "email_cc": cls.partner_cc.email,
                "email_bcc": cls.partner_bcc.email,
            },
        )

    def open_mail_composer_form(self):
        # Based on example in mail_composer_cc_bcc.
        # Use form to populate data
        ctx = {
            "default_partner_ids": self.partner.ids,
            "default_model": self.partner._name,
            "default_res_id": self.partner.id,
            # to ensure consistent test results even when mail_post_defer is installed
            "mail_notify_force_send": True,
        }
        form = Form(self.env["mail.compose.message"].with_context(**ctx))
        form.body = "<p>Hello</p>"
        return form

    def test_email_to_cc(self):
        form = self.open_mail_composer_form()
        composer = form.save()
        # Use object to update Many2many fields (form can't do like this)
        composer.partner_cc_ids = self.partner_cc
        composer.partner_cc_ids |= self.partner_cc2
        composer.partner_bcc_ids = self.partner_bcc
        with self.mock_mail_gateway():
            composer._action_send_mail()
        # Verify recipients of mail.message
        message = self.partner.message_ids[0]
        self.assertEqual(message.email_to, self.partner.email)
        self.assertIn(self.partner_cc.email, message.email_cc)
        self.assertIn(self.partner_cc2.email, message.email_cc)
        self.assertEqual(message.email_bcc, self.partner_bcc.email)

    def test_email_to(self):
        """Test when using email_to directly."""
        Mail = self.env["mail.mail"]
        mail_id = self.mail_template.send_mail(self.partner.id, force_send=True)
        self.assertTrue(mail_id)
        mail = Mail.browse(mail_id)
        message = mail.mail_message_id
        self.assertTrue(message)
        self.assertEqual(message.email_to, self.partner.email)
        self.assertEqual(message.email_cc, self.partner_cc.email)
        # Odoo ignores the email_bcc field in the template!
        # self.assertEqual(message.email_bcc, self.partner_bcc.email)
