# Copyright 2026 Quartile (https://www.quartile.co)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import base64

from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase

PNG_DATA = (
    b"iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8"
    b"z8DwHwAFAAH/q842iQAAAABJRU5ErkJggg=="
)
PNG_DATA_2 = (
    b"iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR4nGP4"
    b"z8DwHwAFAAH/iZk9HQAAAABJRU5ErkJggg=="
)


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
        with self.assertRaises(ValidationError):
            self._create_text_attachment()

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

    def test_write_non_trigger_field_does_not_revalidate(self):
        self.company.attachment_allowed_mimetypes = "text/plain"
        attachment = self._create_text_attachment()
        self.company.attachment_allowed_mimetypes = "image/png"
        attachment.write({"name": "renamed.txt"})

    def test_binary_field_storage_not_restricted(self):
        self.company.attachment_allowed_mimetypes = "text/plain"
        self.partner.image_1920 = PNG_DATA
        attachment = self.Attachment.sudo().search(
            [
                ("res_model", "=", "res.partner"),
                ("res_id", "=", self.partner.id),
                ("res_field", "=", "image_1920"),
            ]
        )
        self.assertEqual(attachment.mimetype, "image/png")
        self.partner.image_1920 = PNG_DATA_2
        self.assertTrue(attachment.exists())

    def test_framework_asset_ir_ui_view_public_bypasses_restriction(self):
        self.company.attachment_allowed_mimetypes = "text/plain"
        attachment = self.Attachment.create(
            {
                "name": "asset_bundle.js",
                "datas": base64.b64encode(b"console.log('bundle')"),
                "res_model": "ir.ui.view",
                "public": True,
            }
        )
        self.assertTrue(attachment)

    def test_url_attachment_bypasses_restriction(self):
        self.company.attachment_allowed_mimetypes = "text/plain"
        attachment = self.Attachment.create(
            {
                "name": "custom.scss",
                "datas": base64.b64encode(b"body { color: red; }"),
                "url": "/web/assets/custom.scss",
            }
        )
        self.assertTrue(attachment)

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
        self.assertEqual(set(attachments.mapped("name")), {"allowed.html"})
        notice = (
            self.env["mail.message"]
            .search([("res_id", "=", self.partner.id), ("model", "=", "res.partner")])
            .filtered(lambda m: "Blocked Attachments" in m.body)
        )
        self.assertEqual(len(notice), 1)
        self.assertIn("blocked.txt", notice.body)

    def test_message_post_filters_blocked_attachment_ids(self):
        self.company.attachment_allowed_mimetypes = ""
        txt_att = self.Attachment.create(
            {
                "name": "will_be_blocked.txt",
                "datas": base64.b64encode(b"text content"),
            }
        )
        png_att = self.Attachment.create(
            {
                "name": "allowed.png",
                "datas": base64.b64encode(base64.b64decode(PNG_DATA)),
            }
        )
        self.company.attachment_allowed_mimetypes = "image/png"
        message = self.partner.message_post(
            body="<p>Test</p>",
            attachment_ids=[txt_att.id, png_att.id],
        )
        self.assertEqual(set(message.attachment_ids.mapped("name")), {"allowed.png"})
        notice = (
            self.env["mail.message"]
            .search([("res_id", "=", self.partner.id), ("model", "=", "res.partner")])
            .filtered(lambda m: "Blocked Attachments" in m.body)
        )
        self.assertEqual(len(notice), 1)
        self.assertIn("will_be_blocked.txt", notice.body)
