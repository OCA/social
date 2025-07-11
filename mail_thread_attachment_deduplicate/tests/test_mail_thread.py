# Copyright 2025 Lambdao
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo.modules.module import get_module_resource
from odoo.tests import TransactionCase


class TestMailDeduplicate(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        vals_customer = {"name": "Cow", "email": "cow@milk.me"}
        cls.customer = cls.env["res.partner"].create(vals_customer)

    def test_mail_deduplicate(self):
        # we receive a mail from the customer related to his own res.partner
        # the mail which contains an embedded image (typically the suer signature)
        self.customer.message_ids.message_id = (
            "<175290809903340.1751622377.487310171127319-openerp-9-res.partner@lambdao>"
        )
        with open(
            get_module_resource(
                "mail_thread_attachment_deduplicate", "tests", "sent.eml"
            ),
            "rb",
        ) as request_file:
            request_message = request_file.read()

        message_1 = request_message.replace(b"XXXID", b"7ecf70df-9e29-4619-984b")
        self.env["mail.thread"].message_process("res.partner", message_1)
        self.assertEqual(len(self.customer.message_ids), 2)
        self.assertEqual(self.customer.message_attachment_count, 1)

        message_2 = request_message.replace(b"XXXID", b"8abf70df-9e29-4619-123c")
        self.env["mail.thread"].message_process("res.partner", message_2)
        self.assertEqual(len(self.customer.message_ids), 3)

        self.customer._compute_message_attachment_count()
        self.assertEqual(self.customer.message_attachment_count, 1)
