# Copyright 2017 Tecnativa - Pedro M. Baeza
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo.tests import common


class TestMailDebrand(common.TransactionCase):
    def setUp(self):
        super().setUp()
        self.default_arch = self.env.ref(
            'mail.message_notification_email'
        ).arch
        self.paynow_arch = self.env.ref(
            'mail.mail_notification_paynow'
        ).arch

    def test_default_debrand(self):
        self.assertIn('using', self.default_arch)
        res = self.env["mail.template"]._debrand_body(self.default_arch)
        self.assertNotIn('using', res)

    def test_paynow_debrand(self):
        self.assertIn('Powered by', self.paynow_arch)
        res = self.env["mail.template"]._debrand_body(self.paynow_arch)
        self.assertNotIn('Powered by', res)
