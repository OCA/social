# Copyright 2026 Domatix <https://www.domatix.cloud>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import base64
from unittest.mock import MagicMock, patch
from urllib.parse import parse_qs, urlparse

from odoo import Command
from odoo.exceptions import UserError
from odoo.tests import HttpCase, TransactionCase, tagged
from odoo.tools import mute_logger

from odoo.addons.social_media_base.tools import media_attachment_token

PATCH_POST = "odoo.addons.social_media_instagram.models.social_account.requests.post"
PATCH_GET = "odoo.addons.social_media_instagram.models.social_account.requests.get"
PATCH_SESSION = (
    "odoo.addons.social_media_instagram.models.social_account.requests.Session"
)


class TestSocialMediaInstagram(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.media = cls.env.ref("social_media_instagram.social_media_instagram")
        cls.user = cls.env.user

    def _create_account(self):
        return self.env["social.account"].create(
            {
                "name": "Instagram Test",
                "media_id": self.media.id,
                "user_id": self.user.id,
                "instagram_account_id": "ig-account-id",
                "instagram_access_token": "access-token",
                "instagram_app_id": "app-id",
                "instagram_app_secret": "app-secret",
                "username": "testuser",
            }
        )

    def _mock_response(self, json_data, status_code=200):
        response = MagicMock()
        response.status_code = status_code
        response.json.return_value = json_data
        return response

    def test_media_registered(self):
        self.assertEqual(self.media.media_type, "instagram")

    def test_action_open_account(self):
        action = self.media.action_open_account()
        self.assertEqual(action["type"], "ir.actions.act_window")
        self.assertEqual(action["res_model"], "wizard.social.account")
        self.assertEqual(action["target"], "new")
        self.assertEqual(action["views"], [[False, "form"]])
        self.assertEqual(action["context"], {"default_media_id": self.media.id})

    def test_action_associate_uses_its_own_provider(self):
        wizard = self.env["wizard.social.account"].create(
            {
                "media_id": self.media.id,
                "instagram_app_id": "app-id",
                "instagram_app_secret": "app-secret",
            }
        )
        action = wizard.action_associate_social_account()
        self.assertEqual(action["type"], "ir.actions.act_url")
        parsed = urlparse(action["url"])
        self.assertEqual(parsed.netloc, "www.instagram.com")
        self.assertEqual(parsed.path, "/oauth/authorize")
        query = parse_qs(parsed.query)
        self.assertIn("instagram_business_basic", query["scope"][0])
        self.assertTrue(query["redirect_uri"][0].endswith("/social_instagram/callback"))

    def test_get_access_token_instagram_invalid_state(self):
        with self.assertRaises(UserError):
            self.env["social.account"].get_access_token_instagram("code", "bad-state")

    @patch(PATCH_GET)
    @patch(PATCH_POST)
    def test_get_access_token_instagram(self, mock_post, mock_get):
        self.env["wizard.social.account"].create(
            {
                "media_id": self.media.id,
                "instagram_app_id": "app-id",
                "instagram_app_secret": "app-secret",
                "csrf_state_token": "state-token",
            }
        )
        mock_post.return_value = self._mock_response({"access_token": "new-token"})
        mock_get.return_value = self._mock_response(
            {"access_token": "long-lived-token", "expires_in": 5184000}
        )
        app_id, app_secret, token, expires_in = self.env[
            "social.account"
        ].get_access_token_instagram("code", "state-token")
        self.assertEqual(app_id, "app-id")
        self.assertEqual(app_secret, "app-secret")
        self.assertEqual(token, "long-lived-token")
        self.assertEqual(expires_in, 5184000)

    @patch(PATCH_GET)
    def test_create_instagram_accounts(self, mock_get):
        mock_get.return_value = self._mock_response(
            {
                "id": "ig-user-id",
                "username": "testuser",
                "account_type": "BUSINESS",
            }
        )
        self.env["social.account"].create_instagram_accounts(
            "app-id", "app-secret", "access-token"
        )
        account = self.env["social.account"].search(
            [
                ("media_type", "=", "instagram"),
                ("instagram_account_id", "=", "ig-user-id"),
            ],
            limit=1,
        )
        self.assertTrue(account)
        self.assertEqual(account.username, "testuser")
        self.assertEqual(account.instagram_access_token, "access-token")
        self.assertEqual(account.instagram_app_id, "app-id")

    def _instagram_import_response(self, url, **kwargs):
        if url.rstrip("/").endswith("/media") and "children" not in url:
            return self._mock_response(
                {
                    "data": [
                        {
                            "id": "img-1",
                            "caption": "Hello",
                            "media_type": "IMAGE",
                            "media_url": "https://cdn.test/img-1.jpg",
                            "permalink": "https://www.instagram.com/p/img-1/",
                            "timestamp": "2026-08-31T20:02:19+0000",
                        },
                        {
                            "id": "vid-1",
                            "caption": "A reel",
                            "media_type": "VIDEO",
                            "media_url": "https://cdn.test/vid-1.mp4",
                            "thumbnail_url": "https://cdn.test/vid-1.jpg",
                            "permalink": "https://www.instagram.com/p/vid-1/",
                            "timestamp": "2026-08-30T20:02:19+0000",
                        },
                    ]
                }
            )
        if "/children" in url:
            return self._mock_response({"data": []})
        download = MagicMock()
        download.status_code = 200
        download.content = b"binary"
        download.headers = {"Content-Type": "image/jpeg"}
        return download

    @patch(PATCH_GET)
    def test_import_posts(self, mock_get):
        account = self._create_account()
        mock_get.side_effect = self._instagram_import_response
        imported = account._instagram_import_posts()
        self.assertEqual(len(imported), 2)
        image_line = imported.filtered(lambda line: line.remote_ref == "img-1")
        self.assertEqual(image_line.state, "posted")
        self.assertEqual(image_line.author, "Instagram Test")
        self.assertEqual(
            image_line.post_account_url, "https://www.instagram.com/p/img-1/"
        )
        self.assertTrue(image_line.image_ids)
        self.assertTrue(image_line.post_id)
        self.assertEqual(image_line.post_id.message, "Hello")
        self.assertEqual(image_line.post_id.state, "published")
        self.assertEqual(
            image_line.media_refs,
            {str(image_line.image_ids.id): "https://cdn.test/img-1.jpg"},
        )
        video_line = imported.filtered(lambda line: line.remote_ref == "vid-1")
        self.assertTrue(video_line.has_video)
        self.assertTrue(video_line.image_ids)
        # The walk stops at the first publication already imported.
        self.assertFalse(account._instagram_import_posts())

    def test_fields_account_url_empty(self):
        account = self._create_account()
        account.username = False
        urls = dict(account._fields_account_url())
        self.assertNotIn("instagram", urls)

    def test_fields_account_url(self):
        account = self._create_account()
        urls = dict(account._fields_account_url())
        self.assertEqual(urls["instagram"], "https://www.instagram.com/testuser")

    def test_post_instagram_single_image(self):
        account = self._create_account()
        attachment = self.env["ir.attachment"].create(
            {
                "name": "test.jpg",
                "datas": "dGVzdA==",
                "mimetype": "image/jpeg",
            }
        )
        post = self.env["social.post"].create(
            {
                "message": "Test post",
                "account_ids": [(4, account.id)],
                "image_ids": [(4, attachment.id)],
            }
        )
        post_account = self.env["social.post.account"].create(
            {
                "post_id": post.id,
                "account_id": account.id,
                "media_id": self.media.id,
                "message": "Test post",
            }
        )
        session = MagicMock()
        session.post.return_value = self._mock_response({"id": "container-id"})
        with (
            patch(PATCH_SESSION, return_value=session),
            patch(
                PATCH_GET, return_value=self._mock_response({"status_code": "FINISHED"})
            ),
            patch(PATCH_POST, return_value=self._mock_response({"id": "published-id"})),
        ):
            media_id = account._post_instagram_media(post_account)
        self.assertEqual(media_id, "published-id")

    def _create_social_user(self):
        return self.env["res.users"].create(
            {
                "name": "Instagram Social User",
                "login": "social_user_instagram",
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

    def test_a_regular_user_can_publish(self):
        """The credentials are read with ``sudo``, so the responsible user
        publishes without an ``AccessError`` even though the token fields are
        restricted to the system group."""
        account = self._create_account()
        attachment = self.env["ir.attachment"].create(
            {"name": "test.jpg", "datas": "dGVzdA==", "mimetype": "image/jpeg"}
        )
        post = self.env["social.post"].create(
            {
                "message": "Test post",
                "account_ids": [(4, account.id)],
                "image_ids": [(4, attachment.id)],
            }
        )
        post_account = self.env["social.post.account"].create(
            {
                "post_id": post.id,
                "account_id": account.id,
                "media_id": self.media.id,
                "message": "Test post",
            }
        )
        user = self._create_social_user()
        account.user_id = user.id
        session = MagicMock()
        session.post.return_value = self._mock_response({"id": "container-id"})
        with (
            patch(PATCH_SESSION, return_value=session),
            patch(
                PATCH_GET, return_value=self._mock_response({"status_code": "FINISHED"})
            ),
            patch(PATCH_POST, return_value=self._mock_response({"id": "published-id"})),
        ):
            media_id = account.with_user(user)._post_instagram_media(post_account)
        self.assertEqual(media_id, "published-id")

    @patch(PATCH_GET)
    def test_refresh_post_statistics(self, mock_get):
        """The counters Instagram reports land on the publication."""
        account = self._create_account()
        attachment = self.env["ir.attachment"].create(
            {"name": "test.jpg", "datas": "dGVzdA==", "mimetype": "image/jpeg"}
        )
        post = self.env["social.post"].create(
            {
                "message": "Test post",
                "account_ids": [(4, account.id)],
                "image_ids": [(4, attachment.id)],
            }
        )
        line = self.env["social.post.account"].create(
            {
                "post_id": post.id,
                "account_id": account.id,
                "media_id": self.media.id,
                "message": "Test post",
                "remote_ref": "media-id",
                "state": "posted",
            }
        )
        mock_get.return_value = self._mock_response(
            {"like_count": 7, "comments_count": 3}
        )
        refreshed = account._refresh_post_statistics(line)
        self.assertEqual(line.like_count, 7)
        self.assertEqual(line.comment_count, 3)
        self.assertTrue(line.statistics_date)
        self.assertIn(line, refreshed)

    def test_action_post_publishes_and_registers_the_line(self):
        """The publish flow reaches the connector and registers the line."""
        account = self._create_account()
        attachment = self.env["ir.attachment"].create(
            {"name": "test.jpg", "datas": "dGVzdA==", "mimetype": "image/jpeg"}
        )
        post = self.env["social.post"].create(
            {
                "message": "Test post",
                "account_ids": [Command.set(account.ids)],
                "image_ids": [Command.set(attachment.ids)],
            }
        )
        session = MagicMock()
        session.post.return_value = self._mock_response({"id": "container-id"})
        with (
            patch(PATCH_SESSION, return_value=session),
            patch(
                PATCH_GET, return_value=self._mock_response({"status_code": "FINISHED"})
            ),
            patch(PATCH_POST, return_value=self._mock_response({"id": "published-id"})),
        ):
            post.action_create_post_account()
        line = post.post_account_ids
        self.assertEqual(line.state, "posted")
        self.assertEqual(line.remote_ref, "published-id")
        self.assertTrue(line.published_date)
        self.assertEqual(post.state, "published")


@tagged("post_install", "-at_install")
class TestSocialMediaInstagramController(HttpCase):
    def test_image_route_only_serves_the_media_of_a_post(self):
        """The public route must not hand out an arbitrary attachment."""
        post = self.env["social.post"].create({"message": "Test post"})
        media = self.env["ir.attachment"].create(
            {
                "name": "photo.jpg",
                "datas": base64.b64encode(b"testimage"),
                "res_model": "social.post",
                "res_id": post.id,
            }
        )
        unrelated = self.env["ir.attachment"].create(
            {"name": "invoice.pdf", "datas": base64.b64encode(b"secret")}
        )
        token = media_attachment_token(self.env, media.id)
        response = self.url_open(
            f"/social_instagram/get_image/{media.id}?token={token}"
        )
        self.assertEqual(response.status_code, 200)
        response = self.url_open(f"/social_instagram/get_image/{unrelated.id}")
        self.assertEqual(response.status_code, 404)
        response = self.url_open(f"/social_instagram/get_image/{media.id}")
        self.assertEqual(response.status_code, 404)
        response = self.url_open(f"/social_instagram/get_image/{media.id}?token=wrong")
        self.assertEqual(response.status_code, 404)

    def test_video_route_serves_a_signed_video(self):
        post = self.env["social.post"].create({"message": "Test post"})
        media = self.env["ir.attachment"].create(
            {
                "name": "clip.mp4",
                "datas": base64.b64encode(b"testvideo"),
                "res_model": "social.post",
                "res_id": post.id,
            }
        )
        token = media_attachment_token(self.env, media.id)
        response = self.url_open(
            f"/social_instagram/get_video/{media.id}?token={token}"
        )
        self.assertEqual(response.status_code, 200)
        response = self.url_open(f"/social_instagram/get_video/{media.id}")
        self.assertEqual(response.status_code, 404)

    def test_callback_with_an_error_redirects(self):
        self.authenticate("admin", "admin")
        response = self.url_open(
            "/social_instagram/callback?error=access_denied",
            allow_redirects=False,
        )
        self.assertEqual(response.status_code, 303)

    @patch(
        "odoo.addons.social_media_instagram.models.social_account."
        "SocialAccount.create_instagram_accounts"
    )
    @patch(
        "odoo.addons.social_media_instagram.models.social_account."
        "SocialAccount.get_access_token_instagram",
        return_value=("app-id", "app-secret", "access-token", 3600),
    )
    def test_callback_links_the_accounts(self, mock_token, mock_create):
        self.authenticate("admin", "admin")
        response = self.url_open(
            "/social_instagram/callback?code=code&state=state",
            allow_redirects=False,
        )
        self.assertEqual(response.status_code, 303)
        mock_create.assert_called_once_with(
            "app-id", "app-secret", "access-token", 3600
        )

    @patch(
        "odoo.addons.social_media_instagram.models.social_account."
        "SocialAccount.create_instagram_accounts"
    )
    @patch(
        "odoo.addons.social_media_instagram.models.social_account."
        "SocialAccount.get_access_token_instagram",
        return_value=("app-id", "app-secret", False, None),
    )
    def test_callback_without_a_token_redirects(self, mock_token, mock_create):
        self.authenticate("admin", "admin")
        response = self.url_open(
            "/social_instagram/callback?code=code&state=state",
            allow_redirects=False,
        )
        self.assertEqual(response.status_code, 303)
        mock_create.assert_not_called()

    @mute_logger(
        "odoo.addons.social_media_instagram.controllers.social_media_instagram"
    )
    @patch(
        "odoo.addons.social_media_instagram.models.social_account."
        "SocialAccount.get_access_token_instagram",
        side_effect=UserError("refused"),
    )
    def test_callback_with_a_failure_redirects(self, mock_token):
        self.authenticate("admin", "admin")
        response = self.url_open(
            "/social_instagram/callback?code=code&state=state",
            allow_redirects=False,
        )
        self.assertEqual(response.status_code, 303)
