# Copyright 2023 Camptocamp
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from datetime import date

from odoo.tests import Form

from odoo.addons.mail_composer_cc_bcc.tests.test_mail_cc_bcc import TestMailCcBcc


class TestMailCcBccInvoice(TestMailCcBcc):
    def open_invoice_mail_composer_form(self):
        # Use form to populate data
        # init invoice data
        self.test_invoice = test_record = self.test_account_move = self.env[
            "account.move"
        ].create(
            {
                "invoice_date": date(2024, 3, 2),
                "invoice_date_due": date(2024, 3, 10),
                "invoice_line_ids": [
                    (0, 0, {"name": "Line1", "price_unit": 100.0}),
                    (0, 0, {"name": "Line2", "price_unit": 200.0}),
                ],
                "move_type": "out_invoice",
                "name": "invoice test",
                "partner_id": self.env.ref("base.res_partner_2").id,
            }
        )

        self.assertTrue(
            self.test_invoice,
            "Test setup did not succeed. Invoice not found.",
        )
        self.test_invoice.write({"state": "posted"})

        ctx = {
            "active_ids": test_record.ids,
            "default_model": "account.move",
            "default_res_id": test_record.id,
            "mail_notify_force_send": True,
        }
        form = Form(self.env["account.move.send"].with_context(**ctx))
        form.mail_body = "<p>Hello</p>"
        return form

    def test_invoice_mail_cc_bcc(self):
        self.set_company()
        form = self.open_invoice_mail_composer_form()
        form.mail_subject = "Hello"
        composer = form.save()
        with self.mock_mail_gateway():
            composer.action_send_and_print()
        message = self.test_invoice.message_ids[0]
        self.assertEqual(len(message.mail_ids), 1)

        # Only 2 partners (from default_cc/bcc of company) notified
        self.assertEqual(len(message.notified_partner_ids), 2)
        self.assertEqual(len(message.notification_ids), 2)
