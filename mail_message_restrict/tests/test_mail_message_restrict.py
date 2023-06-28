# Copyright 2023 Quartile Limited
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo.exceptions import ValidationError
from odoo.tests import common


class TestMailMessageRestrict(common.TransactionCase):
    def setUp(self):
        super().setUp()
        self.MailMessage = self.env["mail.message"]
        self.MailMessageSubtype = self.env["mail.message.subtype"]
        self.model_1 = self.env["ir.model"].search([], limit=1)
        self.model_2 = self.env["ir.model"].search([], offset=1, limit=1)

        # Setup subtype
        self.subtype_comment = self.env.ref("mail.mt_comment")
        self.subtype_comment.allow_send_model_ids = [(6, 0, self.model_1.ids)]

    def test_create_message_with_comment_type_allowed_model(self):
        # Creating a message with comment type and allowed model
        self.MailMessage.with_context(test_mail_message_restrict=True).create(
            {
                "message_type": "comment",
                "model": self.model_1.model,
                "subtype_id": self.subtype_comment.id,
            }
        )

    def test_create_message_with_comment_type_not_allowed_model(self):
        # Creating a message with comment type and not allowed model
        with self.assertRaises(ValidationError):
            self.MailMessage.with_context(test_mail_message_restrict=True).create(
                {
                    "message_type": "comment",
                    "model": self.model_2.model,
                    "subtype_id": self.subtype_comment.id,
                }
            )
