# Copyright 2017 ForgeFlow S.L.
#   (http://www.forgeflow.com)
# Copyright 2025 Quartile (https://www.quartile.co)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo.tests.common import TransactionCase


class TestBaseSearchMailContent(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Partner = cls.env["res.partner"]
        cls.partner_test = cls.Partner.create({"name": "Test Partner"})

    def test_mail_message_get_views(self):
        res = self.env["discuss.channel"].get_views(
            [[False, "search"]],
            {"load_fields": False, "load_filters": True, "toolbar": True},
        )
        self.assertIn(
            "message_search",
            res["models"]["discuss.channel"]["fields"],
            "message_search field was not detected",
        )

    def test_mail_message_search_with_multi_strings_en(self):
        self.partner_test.message_post(body="This is a test message.")
        partner = self.Partner.search([("message_search", "ilike", "test mess")])
        self.assertEqual(partner, self.partner_test)
        partner = self.Partner.search([("message_search", "ilike", "mess test")])
        self.assertEqual(partner, self.partner_test)
        partner = self.Partner.search([("message_search", "ilike", "messy test")])
        self.assertFalse(partner)

    def test_mail_message_search_with_multi_strings_ja(self):
        self.partner_test.message_post(body="これはテスト用のメッセージです。")
        partner = self.Partner.search([("message_search", "ilike", "テスト　です　")])
        self.assertEqual(partner, self.partner_test)
        partner = self.Partner.search([("message_search", "ilike", "です　テスト　")])
        self.assertEqual(partner, self.partner_test)
        partner = self.Partner.search([("message_search", "ilike", "ですわ　テスト")])
        self.assertFalse(partner)
