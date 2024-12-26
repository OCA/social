# Copyright 2025 Jérémy Didderen
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).


from odoo.addons.account.tests.test_account_move_send import TestAccountMoveSendCommon


class TestMailOptionalFollowernotificationsAccount(TestAccountMoveSendCommon):
    def _send_mail(self, recipients, notify_followers, invoice):
        old_messages = self.env["mail.message"].search([])
        wizard = self.create_send_and_print(invoice)
        wizard.notify_followers = notify_followers
        wizard.mail_partner_ids = recipients
        wizard.action_send_and_print()
        return self.env["mail.message"].search([]) - old_messages

    def test_invoice_without_followers(self):
        invoice = self.init_invoice(
            "out_invoice", partner=self.partner_a, amounts=[1000], post=True
        )
        message = self._send_mail(
            recipients=self.partner_b, notify_followers=False, invoice=invoice
        )
        self.assertEqual(
            message.notification_ids.mapped("res_partner_id"),
            self.partner_b,
        )

    def test_invoice_with_followers(self):
        invoice = self.init_invoice(
            "out_invoice", partner=self.partner_a, amounts=[1000], post=True
        )
        message = self._send_mail(
            recipients=self.partner_b, notify_followers=True, invoice=invoice
        )
        self.assertEqual(
            message.notification_ids.mapped("res_partner_id"),
            self.partner_a + self.partner_b,
        )
