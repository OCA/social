# Copyright 2025 Lambdao
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from os.path import join

from odoo.tests import TransactionCase
from odoo.tools.misc import file_path


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
        path = join("mail_thread_attachment_deduplicate", "tests", "sent.eml")
        full_path = file_path(path)
        with open(full_path, "rb") as request_file:
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

    def test_deduplicate_with_body_references(self):
        vals_attachment = {
            "name": "test_image.jpg",
            "raw": b"Test image binary data",
            "res_id": self.customer.id,
            "res_model": "res.partner",
            "mimetype": "image/jpeg",
        }
        existing_attachment = self.env["ir.attachment"].create(vals_attachment)

        # Create a duplicate attachment (same content, different ID)
        duplicate_attachment = self.env["ir.attachment"].create(
            {
                **vals_attachment,
                "res_id": 0,
                "res_model": "mail.compose.message",
            }
        )
        body_with_attachment_ref = f"""
        <div>Test message with inline image</div>
        <div>
            <img src="/web/image/{duplicate_attachment.id}?access_token=old-token"
                 data-attachment-id="{duplicate_attachment.id}"
                 alt="Test Image"
                 class="img img-fluid"/>
        </div>
        """
        msg = self.customer.message_post(
            body=body_with_attachment_ref,
            attachment_ids=[duplicate_attachment.id],
            message_type="comment",
        )
        # The duplicate attachment was not used
        self.assertEqual(msg.attachment_ids, existing_attachment)
        self.assertNotEqual(msg.attachment_ids.id, duplicate_attachment.id)

        message_body = msg.body
        self.assertIn(f"/web/image/{existing_attachment.id}", message_body)
        self.assertIn(f"access_token={existing_attachment.access_token}", message_body)

        # Old references are gone
        self.assertNotIn(f"/web/image/{duplicate_attachment.id}", message_body)
        self.assertNotIn(
            f'data-attachment-id="{duplicate_attachment.id}"', message_body
        )
        self.assertNotIn("access_token=old-token", message_body)

        self.customer._compute_message_attachment_count()
        self.assertEqual(self.customer.message_attachment_count, 1)

    def test_deduplicate_with_cid_references(self):
        vals_attachment = {
            "name": "signature.png",
            "raw": b"Signature image binary data",
            "res_id": self.customer.id,
            "res_model": "res.partner",
            "mimetype": "image/png",
        }
        existing_attachment = self.env["ir.attachment"].create(vals_attachment)
        existing_attachment.access_token = existing_attachment._generate_access_token()

        # Create attachments list with CID reference (simulates email processing)
        duplicate_content = b"Signature image binary data"  # Same content as existing
        attachments_with_cid = [
            ("signature.png", duplicate_content, {"cid": "signature123@example.com"})
        ]

        # Create message body with CID reference
        body_with_cid = """
        <div>Email message with embedded signature</div>
        <div>
            <img src="cid:signature123@example.com" alt="Signature"/>
        </div>
        <p>Best regards</p>
        """
        msg = self.customer.message_post(
            body=body_with_cid,
            attachments=attachments_with_cid,
            message_type="comment",
        )

        message_body = msg.body
        self.assertNotIn("cid:signature123@example.com", message_body)
        self.assertIn(f"/web/image/{existing_attachment.id}", message_body)
        self.assertIn(f"access_token={existing_attachment.access_token}", message_body)

        self.customer._compute_message_attachment_count()
        self.assertEqual(self.customer.message_attachment_count, 1)
