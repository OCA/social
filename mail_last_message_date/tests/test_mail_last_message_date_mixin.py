# Copyright 2026 Quartile (https://www.quartile.co)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo_test_helper import FakeModelLoader

from odoo.tests import common


class TestMailLastMessageDate(common.TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.loader = FakeModelLoader(cls.env, cls.__module__)
        cls.loader.backup_registry()
        from .test_models import TestMailLastMessage

        cls.loader.update_registry((TestMailLastMessage,))
        cls.record = cls.env[TestMailLastMessage._name].create({"name": "Test Record"})

    @classmethod
    def tearDownClass(cls):
        cls.loader.restore_registry()
        return super().tearDownClass()

    def _create_message(self, message_type="email"):
        return self.env["mail.message"].create(
            {
                "message_type": message_type,
                "model": self.record._name,
                "res_id": self.record.id,
                "body": "Test message",
            }
        )

    def test_update_on_tracked_message_type(self):
        self.record.write({"last_message_date": False})
        message = self._create_message()
        self.assertEqual(self.record.last_message_date, message.date)

    def test_no_update_on_untracked_message_type(self):
        self.record.write({"last_message_date": False})
        self._create_message(message_type="comment")
        self.record.invalidate_cache(["last_message_date"])
        self.assertFalse(self.record.last_message_date)
