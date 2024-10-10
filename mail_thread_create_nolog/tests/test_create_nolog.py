# Copyright 2023 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl)

from odoo.tests.common import TransactionCase


class TestMailThreadCreateNoLog(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner = cls.env["res.partner"].create({"name": "TEST"})
        cls.message_model = cls.env["mail.message"]

    def test_message_fetch_with_record(self):
        domain = [
            ("model", "=", self.partner._name),
            ("res_id", "=", self.partner.id),
        ]
        create_msg = self.message_model._generate_messsage(domain)
        # We get a creation message
        self.assertEqual(create_msg["model"], self.partner._name)
        self.assertEqual(create_msg["res_id"], self.partner.id)
        self.assertEqual(create_msg["author"]["id"], self.env.user.partner_id.id)
        self.assertEqual(create_msg["body"], self.partner._creation_message())
        # But it doesn't exist in the DB
        self.assertFalse(self.message_model.browse(create_msg["id"]).exists())

    def test_message_fetch_without_record(self):
        domain = [
            ("model", "=", self.partner._name),
        ]
        create_msg = self.message_model._generate_messsage(domain)
        # If we get no message, the test is OK as well
        if create_msg:
            # The last message is not the 'creation' one
            self.assertNotEqual(create_msg["res_id"], self.partner.id)
            self.assertNotEqual(create_msg["body"], self.partner._creation_message())
            # And it exists in the DB
            self.assertTrue(self.message_model.browse(create_msg["id"]).exists())
