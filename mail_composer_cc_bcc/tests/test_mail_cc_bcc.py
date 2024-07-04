# Copyright 2023 Camptocamp
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import hashlib
import inspect

from odoo import tools
from odoo.tests import Form

from odoo.addons.mail.models.mail_mail import MailMail as upstream
from odoo.addons.mail.tests.test_mail_composer import TestMailComposer

VALID_HASHES = [
    "5f8b9bd28ccfe4f4ef1702002b2ab3fc",
    "0e47779dfd6e70de1cc1457792c68c0f",
    "a918e6f4fc0577cda7680d026ac85278",
]


class TestMailCcBcc(TestMailComposer):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        env = cls.env
        cls.partner = env.ref("base.res_partner_address_31")
        cls.partner_cc = env.ref("base.partner_demo")
        cls.partner_cc2 = env.ref("base.partner_demo_portal")
        cls.partner_cc3 = env.ref("base.res_partner_main1")
        cls.partner_bcc = env.ref("base.res_partner_main2")

    def open_mail_composer_form(self):
        # Use form to populate data
        test_record = self.test_record.with_env(self.env)
        ctx = {
            "default_partner_ids": test_record.ids,
            "default_model": test_record._name,
            "default_res_id": test_record.id,
        }
        form = Form(self.env["mail.compose.message"].with_context(**ctx))
        form.body = "<p>Hello</p>"
        return form

    def open_invoice_mail_composer_form(self):
        # Use form to populate data
        for_name = [("name", "like", "%INV/20__/00003")]
        self.test_invoice = test_record = self.env["account.move"].search(for_name)
        self.assertTrue(
            self.test_invoice,
            "Test setup did not succeeed. Invoice not found.",
        )
        ctx = {
            "active_ids": test_record.ids,
            "default_model": "account.move",
            "default_res_id": test_record.id,
        }
        form = Form(self.env["account.invoice.send"].with_context(**ctx))
        form.body = "<p>Hello</p>"
        return form

    def test_upstream_file_hash(self):
        """Test that copied upstream function hasn't received fixes"""
        func = inspect.getsource(upstream._send).encode()
        func_hash = hashlib.md5(func).hexdigest()
        self.assertIn(func_hash, VALID_HASHES)

    def test_email_cc_bcc(self):
        form = self.open_mail_composer_form()
        composer = form.save()
        # Use object to update Many2many fields (form can't do like this)
        composer.partner_cc_ids = self.partner_cc
        composer.partner_cc_ids |= self.partner_cc2
        composer.partner_cc_ids |= self.partner_cc3
        composer.partner_bcc_ids = self.partner_bcc

        with self.mock_mail_gateway():
            composer._action_send_mail()

        # Verify recipients of mail.message
        message = self.test_record.message_ids[0]
        self.assertEqual(len(message.recipient_cc_ids), 3)
        self.assertEqual(len(message.recipient_bcc_ids), 1)
        # Verify notification
        for_message = [
            ("mail_message_id", "=", message.id),
            ("notification_type", "=", "email"),
        ]
        notif = self.env["mail.notification"].search(for_message)
        self.assertEqual(len(notif), 5)
        # Verify data of mail.mail
        mail = message.mail_ids
        expecting = ", ".join(
            [
                '"Marc Demo" <mark.brown23@example.com>',
                '"Joel Willis" <joel.willis63@example.com>',
                '"Chester Reed" <chester.reed79@example.com>',
            ]
        )
        self.assertEqual(mail.email_cc, expecting)
        expecting = '"Dwayne Newman" <dwayne.newman28@example.com>'
        self.assertEqual(mail.email_bcc, expecting)

    def test_template_cc_bcc(self):
        env = self.env
        # Company default values
        env.company.default_partner_cc_ids = self.partner_cc3
        env.company.default_partner_bcc_ids = self.partner_cc2
        # Product template values
        tmpl_model = env["ir.model"].search([("model", "=", "product.template")])
        partner_cc = self.partner_cc
        partner_bcc = self.partner_bcc
        vals = {
            "name": "Product Template: Re: [E-COM11] Cabinet with Doors",
            "model_id": tmpl_model.id,
            "subject": "Re: [E-COM11] Cabinet with Doors",
            "body_html": """<p style="margin:0px 0 12px 0;box-sizing:border-box;">
Test Template<br></p>""",
            "email_cc": tools.formataddr(
                (partner_cc.name or "False", partner_cc.email or "False")
            ),
            "email_bcc": tools.formataddr(
                (partner_bcc.name or "False", partner_bcc.email or "False")
            ),
        }
        prod_tmpl = env["mail.template"].create(vals)
        # Open mail composer form and check for default values from company
        form = self.open_mail_composer_form()
        composer = form.save()
        self.assertEqual(composer.partner_cc_ids, self.partner_cc3)
        self.assertEqual(composer.partner_bcc_ids, self.partner_cc2)
        # Change email template and check for values from it
        form.template_id = prod_tmpl
        composer = form.save()
        # Beside existing Cc and Bcc, add template's ones
        form = Form(composer)
        form.template_id = prod_tmpl
        composer = form.save()
        expecting = self.partner_cc3 + self.partner_cc
        self.assertEqual(composer.partner_cc_ids, expecting)
        expecting = self.partner_cc2 + self.partner_bcc
        self.assertEqual(composer.partner_bcc_ids, expecting)
        # But not add Marc Demo from cc field to partner_ids field
        self.assertEqual(len(composer.partner_ids), 1)
        self.assertEqual(composer.partner_ids.display_name, "Test")
        # Selecting the template again doesn't add as the partners already
        # in the list
        form = Form(composer)
        form.template_id = env["mail.template"]
        form.save()
        self.assertFalse(form.template_id)
        form.template_id = prod_tmpl
        composer = form.save()
        expecting = self.partner_cc3 + self.partner_cc
        self.assertEqual(composer.partner_cc_ids, expecting)
        expecting = self.partner_cc2 + self.partner_bcc
        self.assertEqual(composer.partner_bcc_ids, expecting)

    def set_company(self):
        company = self.env.company
        # Company default values
        company.default_partner_cc_ids = self.partner_cc3
        company.default_partner_bcc_ids = self.partner_cc2

    def test_recipient_ids_and_cc_bcc(self):
        self.set_company()
        form = self.open_mail_composer_form()
        composer = form.save()
        composer.partner_ids = self.partner + self.partner_cc

        with self.mock_mail_gateway():
            composer._action_send_mail()
        message = self.test_record.message_ids[0]
        self.assertEqual(len(message.mail_ids), 1)
        # Only 4 partners notified
        self.assertEqual(len(message.notified_partner_ids), 4)
        self.assertEqual(len(message.notification_ids), 4)

    def test_invoice_mail_cc_bcc(self):
        self.set_company()
        form = self.open_invoice_mail_composer_form()
        form.subject = "Hello"
        composer = form.save()
        with self.mock_mail_gateway():
            composer._send_email()
        message = self.test_invoice.message_ids[0]
        self.assertEqual(len(message.mail_ids), 1)
        # Only 4 partners notified
        self.assertEqual(len(message.notified_partner_ids), 4)
        self.assertEqual(len(message.notification_ids), 4)

    def test_mail_without_cc_bcc(self):
        # Test without any partner in cc/bcc -> only 1 mail should be sent
        self.set_company()
        form = self.open_mail_composer_form()
        subject = "Testing without cc/bcc single mail"
        form.subject = subject
        composer = form.save()
        composer.partner_cc_ids = None
        composer.partner_bcc_ids = None
        composer.partner_ids = self.partner + self.partner_cc
        ctx = {"mail_notify_force_send": True}
        ctx.update(composer.env.context)
        composer = composer.with_context(**ctx)
        with self.mock_mail_gateway():
            composer._action_send_mail()
        sent_mails = 0
        for mail in self._mails:
            if subject == mail.get("subject"):
                sent_mails += 1
        self.assertEqual(sent_mails, 1)
