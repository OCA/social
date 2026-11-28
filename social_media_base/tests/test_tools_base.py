# Copyright 2026 Binhex <https://www.binhex.cloud>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo.tests import TransactionCase

from odoo.addons.social_media_base.tools import (
    is_media_attachment,
    is_media_request_valid,
    media_attachment_token,
)


class TestToolsBase(TransactionCase):
    def test_a_media_attachment_belongs_to_a_post(self):
        post = self.env["social.post"].create({"message": "Test post"})
        media = self.env["ir.attachment"].create(
            {
                "name": "photo.png",
                "datas": "dGVzdA==",
                "res_model": "social.post",
                "res_id": post.id,
            }
        )
        self.assertTrue(is_media_attachment(media))

    def test_an_attachment_of_another_model_is_not_a_media(self):
        partner = self.env["res.partner"].create({"name": "Test"})
        attachment = self.env["ir.attachment"].create(
            {
                "name": "report.pdf",
                "datas": "dGVzdA==",
                "res_model": "res.partner",
                "res_id": partner.id,
            }
        )
        self.assertFalse(is_media_attachment(attachment))

    def test_a_detached_attachment_is_not_a_media(self):
        attachment = self.env["ir.attachment"].create(
            {"name": "orphan.bin", "datas": "dGVzdA=="}
        )
        self.assertFalse(is_media_attachment(attachment))

    def test_the_token_signs_the_attachment(self):
        post = self.env["social.post"].create({"message": "Test post"})
        media = self.env["ir.attachment"].create(
            {
                "name": "photo.png",
                "datas": "dGVzdA==",
                "res_model": "social.post",
                "res_id": post.id,
            }
        )
        token = media_attachment_token(self.env, media.id)
        self.assertEqual(len(token), 32)
        self.assertTrue(is_media_request_valid(self.env, media, token))
        self.assertFalse(is_media_request_valid(self.env, media, "wrong"))
