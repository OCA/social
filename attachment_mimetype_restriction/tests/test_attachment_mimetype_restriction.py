# Copyright 2026 Quartile (https://www.quartile.co)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import base64
from email.message import EmailMessage

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
        # Composer drafts follow the target model's list, not the company's.
        draft_vals = {
            "name": "draft.txt",
            "datas": base64.b64encode(b"draft"),
            "res_model": "mail.compose.message",
            "res_id": 0,
        }
        self.Attachment.with_context(
            attachment_mimetype_target=("res.partner", self.partner.id)
        ).create(draft_vals)
        draft = self.Attachment.create(draft_vals)
        self.partner.message_post(body="<p>Test</p>", attachment_ids=[draft.id])
        self.assertEqual(draft.res_model, "res.partner")

    def test_per_model_empty_falls_through_to_global(self):
        self.company.attachment_allowed_mimetypes = "image/png"
        self.partner_model.attachment_allowed_mimetypes = ""
        with self.assertRaises(ValidationError):
            self._create_text_attachment(
                res_model="res.partner", res_id=self.partner.id
            )
        draft = self._create_text_attachment(res_model="mail.compose.message", res_id=0)
        with self.assertRaises(ValidationError):
            self.partner.message_post(body="<p>Test</p>", attachment_ids=[draft.id])
        # Portal drafts are checked at upload, as they can be served by token.
        portal_user = self.env["res.users"].create(
            {
                "name": "Portal",
                "login": "portal_mimetype",
                "groups_id": [(6, 0, [self.env.ref("base.group_portal").id])],
            }
        )
        with self.assertRaises(ValidationError):
            self.Attachment.with_user(portal_user).sudo().create(
                {
                    "name": "portal.txt",
                    "datas": base64.b64encode(b"portal"),
                    "res_model": "mail.compose.message",
                    "res_id": 0,
                }
            )

    def test_write_revalidates_on_datas_change(self):
        self.company.attachment_allowed_mimetypes = "text/plain"
        attachment = self._create_text_attachment()
        self.company.attachment_allowed_mimetypes = "image/png"
        with self.assertRaises(ValidationError):
            attachment.write({"datas": base64.b64encode(b"updated content")})

    def test_binary_field_storage_not_restricted(self):
        """Image field storage passes on create and on replace (write path)."""
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

    def test_message_post_filters_blocked_attachments(self):
        self.company.attachment_allowed_mimetypes = "text/html,message/rfc822"
        forwarded = EmailMessage()
        forwarded.set_content("forwarded body")
        self.partner.message_post(
            body="<p>Email</p>",
            attachments=[
                ("blocked.txt", b"blocked content"),
                ("allowed.html", b"<html>allowed</html>"),
                ("forwarded.eml", forwarded),
            ],
        )
        attachments = self.Attachment.search(
            [("res_model", "=", "res.partner"), ("res_id", "=", self.partner.id)]
        )
        self.assertEqual(
            set(attachments.mapped("name")), {"allowed.html", "forwarded.eml"}
        )
        notice = (
            self.env["mail.message"]
            .search([("res_id", "=", self.partner.id), ("model", "=", "res.partner")])
            .filtered(lambda m: "Security Notice" in m.body)
        )
        self.assertEqual(len(notice), 1)
        self.assertIn("blocked.txt", notice.body)
