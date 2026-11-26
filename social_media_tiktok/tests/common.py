# Copyright 2026 Domatix <https://www.domatix.cloud>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import base64
from unittest.mock import MagicMock

from odoo import Command
from odoo.tests import TransactionCase

# A 1x1 transparent PNG, for the avatars the account stores.
PNG_1X1 = (
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB"
    "0C8AAAAASUVORK5CYII="
)


class TikTokCommon(TransactionCase):
    """Fixtures shared by the TikTok tests."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.media = cls.env.ref("social_media_tiktok.social_media_tiktok")
        cls.other_media = cls.env["social.media"].create(
            {"name": "Other media", "media_type": False}
        )
        cls.other_account = cls.env["social.account"].create(
            {
                "name": "Other account",
                "media_id": cls.other_media.id,
                "user_id": cls.env.user.id,
                "remote_ref": "other-ref",
            }
        )

    def _create_account(self, media=None, **values):
        media = media or self.media
        vals = {
            "name": "TikTok Test",
            "media_id": media.id,
            "user_id": self.env.user.id,
            "remote_ref": "open-id",
            "tiktok_username": "testuser",
            "tiktok_access_token": "access-token",
            "tiktok_refresh_token": "refresh-token",
            "tiktok_client_key": "key",
            "tiktok_client_secret": "secret",
            "tiktok_token_expiration_date": "2099-01-01 00:00:00",
        }
        vals.update(values)
        return self.env["social.account"].create(vals)

    def _response(self, json_data=None, status_code=200, text="", content=b"binary"):
        response = MagicMock()
        response.status_code = status_code
        response.text = text
        response.content = content
        if json_data is None:
            response.json.side_effect = ValueError("no json")
        else:
            response.json.return_value = json_data
        return response

    def _video(self, data=b"testvideo", **values):
        vals = {
            "name": "clip.mp4",
            "datas": base64.b64encode(data),
            "mimetype": "video/mp4",
        }
        vals.update(values)
        return self.env["ir.attachment"].create(vals)

    def _image(self, data=b"testimage"):
        return self.env["ir.attachment"].create(
            {
                "name": "test.jpg",
                "datas": base64.b64encode(data),
                "mimetype": "image/jpeg",
            }
        )

    def _create_post(self, account=None, message="Test post", images=None, videos=None):
        account = account or self._create_account()
        vals = {
            "message": message,
            "account_ids": [Command.set(account.ids)],
        }
        if images:
            vals["image_ids"] = [Command.set(images.ids)]
        if videos:
            vals["video_ids"] = [Command.set(videos.ids)]
        return self.env["social.post"].create(vals)

    def _create_line(self, account=None, post=None, message="Test post", **values):
        account = account or self._create_account()
        post = post or self._create_post(account, message=message)
        vals = {
            "post_id": post.id,
            "account_id": account.id,
            "media_id": account.media_id.id,
            "message": message,
        }
        vals.update(values)
        return self.env["social.post.account"].create(vals)

    def _create_social_user(self, login):
        return self.env["res.users"].create(
            {
                "name": login,
                "login": login,
                "group_ids": [
                    Command.set(
                        [
                            self.env.ref("base.group_user").id,
                            self.env.ref(
                                "social_media_base.group_social_media_user"
                            ).id,
                        ]
                    )
                ],
            }
        )

    def _create_wizard(self, media=None, **values):
        media = media or self.media
        vals = {"media_id": media.id}
        vals.update(values)
        return self.env["wizard.social.account"].create(vals)
