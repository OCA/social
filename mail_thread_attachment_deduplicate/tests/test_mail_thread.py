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

    def test_deduplicate_outgoing(self):
        # it's not a very good test, since we're hard coding assumptions about
        # how the code works, which could change in the future
        # but the controller is called from the JS when adding a file to a message
        # to be sent, so the alternative is a rube-goldberg test that isn't very
        # interesting anyway.
        vals_attachment = {
            "name": "msg.txt",
            "raw": b"Message binary data",
            "res_id": 0,
            "res_model": "mail.compose.message",
        }
        # mail_attachment_upload would create something like this
        attachment = self.env["ir.attachment"].create(vals_attachment.copy())

        vals_message = {
            "body": "Message body",
            "subject": None,
            "message_type": "comment",
            "email_from": None,
            "author_id": None,
            "parent_id": False,
            "subtype_xmlid": "mail.mt_comment",
            "subtype_id": False,
            "partner_ids": [],
            "attachments": None,
        }
        msg_count = len(self.customer.message_ids)
        msg_1 = self.customer.message_post(
            **vals_message.copy(), attachment_ids=[attachment.id]
        )
        self.assertEqual(len(self.customer.message_ids), msg_count + 1)
        self.assertEqual(msg_1.attachment_ids, attachment)

        self.assertEqual(self.customer.message_attachment_count, 1)

        attachment_dup = self.env["ir.attachment"].create(vals_attachment)
        msg_2 = self.customer.message_post(
            **vals_message.copy(), attachment_ids=[attachment_dup.id]
        )
        self.assertEqual(len(self.customer.message_ids), msg_count + 2)

        self.customer._compute_message_attachment_count()
        self.assertEqual(self.customer.message_attachment_count, 1)
        self.assertEqual(msg_2.attachment_ids, attachment)
