# Copyright 2026 Domatix <https://www.domatix.cloud>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import base64
from unittest.mock import MagicMock, patch

from odoo import Command
from odoo.exceptions import UserError
from odoo.tests import HttpCase, TransactionCase, tagged
from odoo.tools import mute_logger

from odoo.addons.social_media_base.tools import media_attachment_token

PATCH_POST = "odoo.addons.social_media_facebook.models.social_account.requests.post"
PATCH_GET = "odoo.addons.social_media_facebook.models.social_account.requests.get"
PATCH_POST_ACCOUNT_POST = (
    "odoo.addons.social_media_facebook.models.social_post_account.requests.post"
)
PATCH_POST_ACCOUNT_DELETE = (
    "odoo.addons.social_media_facebook.models.social_post_account.requests.delete"
)


class TestSocialMediaFacebook(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.media = cls.env.ref("social_media_facebook.social_media_facebook")
        cls.user = cls.env.user

    def _create_account(self):
        return self.env["social.account"].create(
            {
                "name": "Facebook Test",
                "media_id": self.media.id,
                "user_id": self.user.id,
                "facebook_account_id": "page-id",
                "facebook_access_token": "access-token",
                "facebook_app_id": "app-id",
                "facebook_app_secret": "app-secret",
            }
        )

    def _mock_response(self, json_data, status_code=200):
        response = MagicMock()
        response.status_code = status_code
        response.json.return_value = json_data
        return response

    def test_media_registered(self):
        self.assertEqual(self.media.media_type, "facebook")

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
                "facebook_app_id": "app-id",
                "facebook_app_secret": "app-secret",
            }
        )
        action = wizard.action_associate_social_account()
        self.assertEqual(action["type"], "ir.actions.act_url")
        self.assertIn("facebook.com", action["url"])

    def test_get_access_token_facebook_invalid_state(self):
        with self.assertRaises(UserError):
            self.env["social.account"].get_access_token_facebook("code", "bad-state")

    @patch(PATCH_GET)
    @patch(PATCH_POST)
    def test_get_access_token_facebook(self, mock_post, mock_get):
        self.env["wizard.social.account"].create(
            {
                "media_id": self.media.id,
                "facebook_app_id": "app-id",
                "facebook_app_secret": "app-secret",
                "csrf_state_token": "state-token",
            }
        )
        mock_post.return_value = self._mock_response({"access_token": "new-token"})
        mock_get.return_value = self._mock_response(
            {"access_token": "long-lived-token"}
        )
        app_id, app_secret, token = self.env[
            "social.account"
        ].get_access_token_facebook("code", "state-token")
        self.assertEqual(app_id, "app-id")
        self.assertEqual(app_secret, "app-secret")
        self.assertEqual(token, "long-lived-token")

    def test_fields_account_url_empty(self):
        account = self._create_account()
        account.facebook_account_id = False
        urls = dict(account._fields_account_url())
        self.assertNotIn("facebook", urls)

    def test_fields_account_url(self):
        account = self._create_account()
        urls = dict(account._fields_account_url())
        self.assertEqual(urls["facebook"], "https://www.facebook.com/page-id")

    @patch(PATCH_POST)
    def test_post_facebook_text(self, mock_post):
        account = self._create_account()
        post = self.env["social.post"].create(
            {
                "message": "Test post",
                "account_ids": [(4, account.id)],
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
        mock_post.return_value = self._mock_response({"id": "post-id"})
        result = account._post_facebook(post_account)
        self.assertEqual(result, "post-id")

    @patch(PATCH_POST_ACCOUNT_DELETE)
    def test_delete_facebook_comment(self, mock_delete):
        account = self._create_account()
        post = self.env["social.post"].create(
            {"message": "Test post", "account_ids": [(4, account.id)]}
        )
        post_account = self.env["social.post.account"].create(
            {
                "post_id": post.id,
                "account_id": account.id,
                "media_id": self.media.id,
                "message": "Test post",
            }
        )
        mock_delete.return_value = self._mock_response({})
        result = post_account.delete_facebook_comment("comment-id")
        self.assertTrue(result["success"])

    def _create_social_user(self):
        return self.env["res.users"].create(
            {
                "name": "Facebook Social User",
                "login": "social_user_facebook",
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

    @patch(PATCH_POST)
    def test_a_regular_user_can_publish(self, mock_post):
        """The credentials are read with ``sudo``, so the responsible user
        publishes without an ``AccessError`` even though the token fields are
        restricted to the system group."""
        account = self._create_account()
        post = self.env["social.post"].create(
            {"message": "Test post", "account_ids": [(4, account.id)]}
        )
        post_account = self.env["social.post.account"].create(
            {
                "post_id": post.id,
                "account_id": account.id,
                "media_id": self.media.id,
                "message": "Test post",
            }
        )
        mock_post.return_value = self._mock_response({"id": "post-id"})
        user = self._create_social_user()
        account.user_id = user.id
        result = account.with_user(user)._post_facebook(post_account)
        self.assertEqual(result, "post-id")

    @patch(PATCH_GET)
    def test_refresh_post_statistics(self, mock_get):
        """The counters Facebook reports land on the publication."""
        account = self._create_account()
        post = self.env["social.post"].create(
            {"message": "Test post", "account_ids": [(4, account.id)]}
        )
        line = self.env["social.post.account"].create(
            {
                "post_id": post.id,
                "account_id": account.id,
                "media_id": self.media.id,
                "message": "Test post",
                "remote_ref": "post-id",
                "state": "posted",
            }
        )
        mock_get.return_value = self._mock_response(
            {
                "id": "post-id",
                "likes": {"summary": {"total_count": 5}},
                "comments": {"summary": {"total_count": 2}},
                "shares": {"count": 1},
            }
        )
        refreshed = account._refresh_post_statistics(line)
        self.assertEqual(line.like_count, 5)
        self.assertEqual(line.comment_count, 2)
        self.assertEqual(line.share_count, 1)
        self.assertTrue(line.statistics_date)
        self.assertIn(line, refreshed)

    @patch(PATCH_POST_ACCOUNT_POST)
    def test_action_post_publishes_and_registers_the_line(self, mock_post):
        """The publish flow reaches the connector and registers the line."""
        account = self._create_account()
        attachment = self.env["ir.attachment"].create(
            {
                "name": "photo.png",
                "datas": base64.b64encode(b"testimage"),
                "res_model": "social.post",
            }
        )
        post = self.env["social.post"].create(
            {
                "message": "Test post",
                "account_ids": [Command.set(account.ids)],
                "image_ids": [Command.set(attachment.ids)],
            }
        )
        mock_post.return_value = self._mock_response({"id": "page-id_1234"})
        post.action_create_post_account()
        line = post.post_account_ids
        self.assertEqual(line.state, "posted")
        self.assertEqual(line.remote_ref, "page-id_1234")
        self.assertTrue(line.published_date)
        self.assertEqual(line.post_account_url, "https://www.facebook.com/page-id_1234")
        self.assertEqual(post.state, "published")

    @mute_logger("odoo.addons.social_media_base.models.social_post_account")
    @patch(PATCH_POST_ACCOUNT_POST)
    def test_action_post_keeps_a_failure_on_its_own_line(self, mock_post):
        """A refused publication is recorded without dropping the post."""
        account = self._create_account()
        post = self.env["social.post"].create(
            {
                "message": "Test post",
                "account_ids": [Command.set(account.ids)],
            }
        )
        mock_post.return_value = self._mock_response(
            {"error": {"message": "Something went wrong"}}, status_code=500
        )
        mock_post.return_value.text = "Something went wrong"
        post.action_create_post_account()
        line = post.post_account_ids
        self.assertEqual(line.state, "failed")
        self.assertIn("Something went wrong", line.failed_description)
        self.assertEqual(post.state, "draft")


@tagged("post_install", "-at_install")
class TestSocialMediaFacebookController(HttpCase):
    def test_image_route_only_serves_the_media_of_a_post(self):
        """The public route must not hand out an arbitrary attachment."""
        post = self.env["social.post"].create({"message": "Test post"})
        media = self.env["ir.attachment"].create(
            {
                "name": "photo.png",
                "datas": base64.b64encode(b"testimage"),
                "res_model": "social.post",
                "res_id": post.id,
            }
        )
        unrelated = self.env["ir.attachment"].create(
            {
                "name": "invoice.pdf",
                "datas": base64.b64encode(b"secret"),
            }
        )
        token = media_attachment_token(self.env, media.id)
        response = self.url_open(f"/social_facebook/get_image/{media.id}?token={token}")
        self.assertEqual(response.status_code, 200)
        response = self.url_open(f"/social_facebook/get_image/{unrelated.id}")
        self.assertEqual(response.status_code, 404)
        response = self.url_open(f"/social_facebook/get_image/{media.id}")
        self.assertEqual(response.status_code, 404)
        response = self.url_open(f"/social_facebook/get_image/{media.id}?token=wrong")
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
        response = self.url_open(f"/social_facebook/get_video/{media.id}?token={token}")
        self.assertEqual(response.status_code, 200)
        response = self.url_open(f"/social_facebook/get_video/{media.id}")
        self.assertEqual(response.status_code, 404)
        response = self.url_open(f"/social_facebook/get_video/{media.id}?token=wrong")
        self.assertEqual(response.status_code, 404)

    def test_callback_with_an_error_redirects(self):
        self.authenticate("admin", "admin")
        response = self.url_open(
            "/social_facebook/callback?error=access_denied",
            allow_redirects=False,
        )
        self.assertEqual(response.status_code, 303)

    @patch(
        "odoo.addons.social_media_facebook.models.social_account."
        "SocialAccount.create_facebook_accounts"
    )
    @patch(
        "odoo.addons.social_media_facebook.models.social_account."
        "SocialAccount.get_access_token_facebook",
        return_value=("app-id", "app-secret", "access-token"),
    )
    def test_callback_links_the_accounts(self, mock_token, mock_create):
        self.authenticate("admin", "admin")
        response = self.url_open(
            "/social_facebook/callback?code=code&state=state",
            allow_redirects=False,
        )
        self.assertEqual(response.status_code, 303)
        mock_create.assert_called_once_with("app-id", "app-secret", "access-token")

    @patch(
        "odoo.addons.social_media_facebook.models.social_account."
        "SocialAccount.create_facebook_accounts"
    )
    @patch(
        "odoo.addons.social_media_facebook.models.social_account."
        "SocialAccount.get_access_token_facebook",
        return_value=("app-id", "app-secret", False),
    )
    def test_callback_without_a_token_redirects(self, mock_token, mock_create):
        self.authenticate("admin", "admin")
        response = self.url_open(
            "/social_facebook/callback?code=code&state=state",
            allow_redirects=False,
        )
        self.assertEqual(response.status_code, 303)
        mock_create.assert_not_called()

    @mute_logger("odoo.addons.social_media_facebook.controllers.social_media_facebook")
    @patch(
        "odoo.addons.social_media_facebook.models.social_account."
        "SocialAccount.get_access_token_facebook",
        side_effect=UserError("refused"),
    )
    def test_callback_with_a_failure_redirects(self, mock_token):
        self.authenticate("admin", "admin")
        response = self.url_open(
            "/social_facebook/callback?code=code&state=state",
            allow_redirects=False,
        )
        self.assertEqual(response.status_code, 303)
