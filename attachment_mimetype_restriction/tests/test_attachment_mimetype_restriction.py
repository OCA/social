# Copyright 2026 Quartile (https://www.quartile.co)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import base64

from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase


class TestAttachmentMimetypeRestriction(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Attachment = cls.env["ir.attachment"]
        cls.IrModel = cls.env["ir.model"]
        cls.company = cls.env.company
        cls.partner = cls.env["res.partner"].create({"name": "Test Partner"})
        cls.partner_model = cls.IrModel.search([("model", "=", "res.partner")])

    def _create_text_attachment(self, **overrides):
        vals = {
            "name": "test_file.txt",
            "datas": base64.b64encode(b"test data"),
        }
        vals.update(overrides)
        return self.Attachment.create(vals)

    def test_non_allowed_mimetype_blocked(self):
        self.company.attachment_allowed_mimetypes = "image/png"
        with self.assertRaises(ValidationError) as cm:
            self._create_text_attachment()
        self.assertIn("text/plain", str(cm.exception))

    def test_allowed_mimetype_create(self):
        self.company.attachment_allowed_mimetypes = "text/plain,application/pdf"
        attachment = self._create_text_attachment()
        self.assertEqual(attachment.mimetype, "text/plain")

    def test_empty_config_allows_all(self):
        self.company.attachment_allowed_mimetypes = ""
        self.assertTrue(self._create_text_attachment())

    def test_per_model_overrides_global(self):
        self.company.attachment_allowed_mimetypes = "image/png"
        self.partner_model.attachment_allowed_mimetypes = "text/plain"
        attachment = self._create_text_attachment(
            res_model="res.partner", res_id=self.partner.id
        )
        self.assertTrue(attachment)

    def test_per_model_empty_falls_through_to_global(self):
        self.company.attachment_allowed_mimetypes = "image/png"
        self.partner_model.attachment_allowed_mimetypes = ""
        with self.assertRaises(ValidationError):
            self._create_text_attachment(
                res_model="res.partner", res_id=self.partner.id
            )

    def test_write_revalidates_on_datas_change(self):
        self.company.attachment_allowed_mimetypes = "text/plain"
        attachment = self._create_text_attachment()
        self.company.attachment_allowed_mimetypes = "image/png"
        with self.assertRaises(ValidationError):
            attachment.write({"datas": base64.b64encode(b"updated content")})

    def test_message_post_filters_blocked_attachments(self):
        self.company.attachment_allowed_mimetypes = "text/html"
        self.partner.message_post(
            body="<p>Email</p>",
            attachments=[
                ("blocked.txt", b"blocked content"),
                ("allowed.html", b"<html>allowed</html>"),
            ],
        )
        attachments = self.Attachment.search(
            [("res_model", "=", "res.partner"), ("res_id", "=", self.partner.id)]
        )
        self.assertEqual(attachments.mapped("name"), ["allowed.html"])
        notice = (
            self.env["mail.message"]
            .search([("res_id", "=", self.partner.id), ("model", "=", "res.partner")])
            .filtered(lambda m: "Security Notice" in m.body)
        )
        self.assertEqual(len(notice), 1)
        self.assertIn("blocked.txt", notice.body)
