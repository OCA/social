# Copyright 2023 Quartile Limited
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo.exceptions import UserError
from odoo.tests import common


class TestMailMessageRestrict(common.TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.message_model = cls.env["mail.message"]
        cls.model_1 = cls.env["ir.model"].search([], limit=1)
        cls.model_2 = cls.env["ir.model"].search([], offset=1, limit=1)
        # Setup subtype
        cls.subtype_comment = cls.env.ref("mail.mt_comment")
        cls.subtype_comment.allow_send_model_ids = [(6, 0, cls.model_1.ids)]

    def test_create_message_with_comment_type_allowed_model(self):
        # Creating a message with comment type and allowed model
        self.message_model.with_context(test_mail_message_restrict=True).create(
            {
                "message_type": "comment",
                "model": self.model_1.model,
                "subtype_id": self.subtype_comment.id,
            }
        )

    def test_create_message_with_comment_type_not_allowed_model(self):
        # Creating a message with comment type and not allowed model
        with self.assertRaises(UserError):
            self.message_model.with_context(test_mail_message_restrict=True).create(
                {
                    "message_type": "comment",
                    "model": self.model_2.model,
                    "subtype_id": self.subtype_comment.id,
                }
            )
