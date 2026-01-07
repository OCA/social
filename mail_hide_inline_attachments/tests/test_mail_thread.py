# Copyright (C) 2024 - KMEE
# License LGPL-3 - See http://www.gnu.org/licenses/lgpl-3.0.html

import base64

from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged("post_install", "-at_install")
class TestMailThreadInlineAttachments(TransactionCase):
    def setUp(self):
        super().setUp()
        self.partner = self.env["res.partner"].create(
            {
                "name": "Test Partner",
                "email": "test@example.com",
            }
        )
        # Base64 encoded 1x1 PNG image
        self.png_data_b64 = (
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwAD"
            "hgGAWjR9awAAAABJRU5ErkJggg=="
        )
        # Decoded PNG bytes for attachments parameter
        self.png_data = base64.b64decode(self.png_data_b64)
        # Base64 encoded minimal PDF
        self.pdf_data_b64 = (
            "JVBERi0xLjQKJeLjz9MNCjEgMCBvYmoKPDwvVHlwZS9DYXRhbG9nL1BhZ2VzIDIgMCBSPj4K"
            "ZW5kb2JqCjIgMCBvYmoKPDwvVHlwZS9QYWdlcz4+CmVuZG9iagp4cmVmCjAgMwowMDAwMDAw"
            "MDAwIDY1NTM1IGYNCjAwMDAwMDAwMTUgMDAwMDAgbg0KMDAwMDAwMDA2MCAwMDAwMCBuDQp0"
            "cmFpbGVyCjw8L1NpemUgMy9Sb290IDEgMCBSPj4Kc3RhcnR4cmVmCjEwOQolJUVPRg=="
        )
        # Decoded PDF bytes for attachments parameter
        self.pdf_data = base64.b64decode(self.pdf_data_b64)

    def test_inline_attachment_via_cid_is_hidden(self):
        """Test that inline attachments referenced via CID are hidden"""
        # Post message with inline attachment using CID
        message = self.partner.message_post(
            body="<p>Test message with inline image: " '<img src="cid:test_cid"/></p>',
            message_type="comment",
            attachments=[("test_image.png", self.png_data, {"cid": "test_cid"})],
        )

        # Get the created attachment
        attachment = message.attachment_ids.filtered(
            lambda a: a.name == "test_image.png"
        )
        self.assertTrue(attachment, "Attachment should be created")

        # Check that inline attachment is not linked to the record
        attachments = self.partner._get_mail_thread_data_attachments()
        self.assertNotIn(
            attachment,
            attachments,
            "Inline attachment with CID should not appear in list",
        )
        # Verify it's unlinked from the record
        attachment.invalidate_recordset()
        self.assertFalse(attachment.res_model)
        self.assertFalse(attachment.res_id)

    def test_regular_attachments_are_shown(self):
        """Test that regular (non-inline) attachments are still shown"""
        # Post message with regular attachment (not referenced in body)
        message = self.partner.message_post(
            body="<p>Test message with attachment</p>",
            message_type="comment",
            attachments=[("test_document.pdf", self.pdf_data)],
        )

        # Get the created attachment
        attachment = message.attachment_ids.filtered(
            lambda a: a.name == "test_document.pdf"
        )
        self.assertTrue(attachment, "Attachment should be created")

        # Check that regular attachment is linked to the record
        attachments = self.partner._get_mail_thread_data_attachments()
        self.assertIn(
            attachment,
            attachments,
            "Regular attachment should appear in attachment list",
        )
        # Verify it's linked to the record
        self.assertEqual(attachment.res_model, "res.partner")
        self.assertEqual(attachment.res_id, self.partner.id)

    def test_mixed_attachments(self):
        """Test with both inline and regular attachments"""
        # Post message with both inline (CID) and regular attachments
        message = self.partner.message_post(
            body='<p>Message with <img src="cid:inline_cid"/> ' "and attachment</p>",
            message_type="comment",
            attachments=[
                ("inline_image.png", self.png_data, {"cid": "inline_cid"}),
                ("document.pdf", self.pdf_data),
            ],
        )

        inline_attachment = message.attachment_ids.filtered(
            lambda a: a.name == "inline_image.png"
        )
        regular_attachment = message.attachment_ids.filtered(
            lambda a: a.name == "document.pdf"
        )

        self.assertTrue(inline_attachment, "Inline attachment should exist")
        self.assertTrue(regular_attachment, "Regular attachment should exist")

        # Check results
        attachments = self.partner._get_mail_thread_data_attachments()
        self.assertNotIn(
            inline_attachment, attachments, "Inline attachment should not appear"
        )
        self.assertIn(
            regular_attachment, attachments, "Regular attachment should appear"
        )
        self.assertEqual(len(attachments), 1)
        # Verify inline is unlinked, regular is linked
        inline_attachment.invalidate_recordset()
        regular_attachment.invalidate_recordset()
        self.assertFalse(inline_attachment.res_model)
        self.assertFalse(inline_attachment.res_id)
        self.assertEqual(regular_attachment.res_model, "res.partner")
        self.assertEqual(regular_attachment.res_id, self.partner.id)

    def test_inline_attachment_via_data_filename(self):
        """Test that inline attachments referenced via data-filename are
        hidden"""
        # Post message with inline attachment using data-filename
        message = self.partner.message_post(
            body="<p>Test message with inline image: "
            '<img src="data:image/png;base64,test" '
            'data-filename="test_image.png"/></p>',
            message_type="comment",
            attachments=[("test_image.png", self.png_data)],
        )

        # Get the created attachment
        attachment = message.attachment_ids.filtered(
            lambda a: a.name == "test_image.png"
        )
        self.assertTrue(attachment, "Attachment should be created")

        # Check that inline attachment is not linked to the record
        attachments = self.partner._get_mail_thread_data_attachments()
        self.assertNotIn(
            attachment,
            attachments,
            "Inline attachment with data-filename should not appear",
        )
        # Verify it's unlinked from the record
        attachment.invalidate_recordset()
        self.assertFalse(attachment.res_model)
        self.assertFalse(attachment.res_id)

    def test_multiple_inline_attachments(self):
        """Test that multiple inline attachments are all hidden"""
        # Post message with multiple inline attachments using CID
        message = self.partner.message_post(
            body='<p>Message with <img src="cid:cid1"/> and '
            '<img src="cid:cid2"/></p>',
            message_type="comment",
            attachments=[
                ("image1.png", self.png_data, {"cid": "cid1"}),
                ("image2.png", self.png_data, {"cid": "cid2"}),
                ("document.pdf", self.pdf_data),
            ],
        )

        inline1 = message.attachment_ids.filtered(lambda a: a.name == "image1.png")
        inline2 = message.attachment_ids.filtered(lambda a: a.name == "image2.png")
        regular = message.attachment_ids.filtered(lambda a: a.name == "document.pdf")

        # Check results
        attachments = self.partner._get_mail_thread_data_attachments()
        self.assertNotIn(inline1, attachments)
        self.assertNotIn(inline2, attachments)
        self.assertIn(regular, attachments)
        self.assertEqual(len(attachments), 1)
        # Verify all inline are unlinked
        inline1.invalidate_recordset()
        inline2.invalidate_recordset()
        self.assertFalse(inline1.res_model)
        self.assertFalse(inline1.res_id)
        self.assertFalse(inline2.res_model)
        self.assertFalse(inline2.res_id)
        self.assertEqual(regular.res_model, "res.partner")
        self.assertEqual(regular.res_id, self.partner.id)
