# Copyright 2023 Camptocamp
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo.tests import Form

from odoo.addons.mail_composer_cc_bcc.tests.test_mail_cc_bcc import TestMailCcBcc


class TestMailCcBccInvoice(TestMailCcBcc):
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
            "mail_notify_force_send": True,
        }
        form = Form(self.env["account.invoice.send"].with_context(**ctx))
        form.body = "<p>Hello</p>"
        return form

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
