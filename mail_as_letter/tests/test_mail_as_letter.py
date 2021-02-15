# Copyright 2016 ACSONE SA/NV
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase


class TestMailAsLetter(TransactionCase):
    def setUp(self):
        super().setUp()

        # ENVIRONMENTS
        self.mail_compose_message = self.env["mail.compose.message"]

        # INSTANCES
        # Partners
        self.base_partner = self.ref("base.main_partner")
        self.partner_demo = self.ref("base.partner_demo")
        # Mail compose message
        self.mail_composer = self.mail_compose_message.create(
            {"subject": "Test mail", "body": "Blah blah blah"}
        )

    def test_compute_partner_count(self):
        # No partner
        self.mail_composer.update({"partner_ids": False})
        self.assertEqual(self.mail_composer.partner_count, 0)
        # One partner
        self.mail_composer.update({"partner_ids": [self.base_partner]})
        self.assertEqual(self.mail_composer.partner_count, 1)
        # Two partners
        self.mail_composer.update(
            {"partner_ids": [self.base_partner, self.partner_demo]}
        )
        self.assertEqual(self.mail_composer.partner_count, 2)

    def test_download_pdf(self):
        # With no partner
        with self.assertRaises(UserError), self.cr.savepoint():
            self.mail_composer.update({"partner_ids": False})
            self.mail_composer.download_pdf()
        # With more than one partner
        with self.assertRaises(UserError), self.cr.savepoint():
            self.mail_composer.update(
                {"partner_ids": [self.base_partner, self.partner_demo]}
            )
            self.mail_composer.download_pdf()
        # With exactly one partner
        self.mail_composer.update({"partner_ids": [self.base_partner]})
        self.mail_composer.download_pdf()
