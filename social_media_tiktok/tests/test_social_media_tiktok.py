# Copyright 2026 Domatix <https://www.domatix.cloud>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from unittest.mock import MagicMock, patch

from odoo.exceptions import UserError
from odoo.tests import HttpCase, TransactionCase, tagged
from odoo.tools import mute_logger

PATCH_POST = "odoo.addons.social_media_tiktok.models.social_account.requests.post"
PATCH_GET = "odoo.addons.social_media_tiktok.models.social_account.requests.get"
PATCH_PUT = "odoo.addons.social_media_tiktok.models.social_account.requests.put"


class TestSocialMediaTikTok(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.media = cls.env.ref("social_media_tiktok.social_media_tiktok")
        cls.user = cls.env.user

    def _create_account(self):
        return self.env["social.account"].create(
            {
                "name": "TikTok Test",
                "media_id": self.media.id,
                "user_id": self.user.id,
                "tiktok_access_token": "access-token",
                "tiktok_refresh_token": "refresh-token",
                "tiktok_client_key": "key",
                "tiktok_client_secret": "secret",
                "tiktok_token_expiration_date": "2099-01-01 00:00:00",
            }
        )

    def _mock_response(self, json_data, status_code=200):
        response = MagicMock()
        response.status_code = status_code
        response.json.return_value = json_data
        return response

    def test_media_registered(self):
        self.assertEqual(self.media.media_type, "tiktok")

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
                "tiktok_client_key": "client-key",
                "tiktok_client_secret": "client-secret",
            }
        )
        action = wizard.action_associate_social_account()
        self.assertEqual(action["type"], "ir.actions.act_url")
        self.assertIn("tiktok.com", action["url"])

    def test_get_access_token_tiktok_invalid_state(self):
        with self.assertRaises(UserError):
            self.env["social.account"].get_access_token_tiktok("code", "bad-state")

    @patch(PATCH_POST)
    def test_get_access_token_tiktok(self, mock_post):
        self.env["wizard.social.account"].create(
            {
                "media_id": self.media.id,
                "tiktok_client_key": "key",
                "tiktok_client_secret": "secret",
                "csrf_state_token": "state-token",
            }
        )
        mock_post.return_value = self._mock_response({"access_token": "new-token"})
        client_key, client_secret, tokens = self.env[
            "social.account"
        ].get_access_token_tiktok("code", "state-token")
        self.assertEqual(client_key, "key")
        self.assertEqual(client_secret, "secret")
        self.assertEqual(tokens["access_token"], "new-token")

    @patch(PATCH_POST)
    def test_refresh_tiktok_token(self, mock_post):
        account = self._create_account()
        account.tiktok_token_expiration_date = "2000-01-01 00:00:00"
        mock_post.return_value = self._mock_response(
            {"access_token": "refreshed-token", "expires_in": 86400}
        )
        token = account._refresh_tiktok_token()
        self.assertEqual(token, "refreshed-token")
        self.assertEqual(account.tiktok_access_token, "refreshed-token")

    def test_refresh_tiktok_token_not_expired(self):
        account = self._create_account()
        token = account._refresh_tiktok_token()
        self.assertEqual(token, "access-token")

    def test_fields_account_url_empty(self):
        account = self._create_account()
        account.tiktok_username = False
        urls = dict(account._fields_account_url())
        self.assertNotIn("tiktok", urls)

    def test_fields_account_url(self):
        account = self._create_account()
        account.tiktok_username = "testuser"
        urls = dict(account._fields_account_url())
        self.assertEqual(urls["tiktok"], "https://www.tiktok.com/@testuser")

    @patch(PATCH_GET)
    def test_update_account_data(self, mock_get):
        account = self._create_account()
        mock_get.return_value = self._mock_response(
            {"data": {"user": {"username": "newuser", "display_name": "New User"}}}
        )
        account._update_account_data()
        self.assertEqual(account.username, "newuser")

    @patch(PATCH_POST)
    def test_refresh_post_statistics(self, mock_post):
        """The counters TikTok reports land on the publication."""
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
                "remote_ref": "video-id",
                "state": "posted",
            }
        )
        mock_post.return_value = self._mock_response(
            {
                "data": {
                    "videos": [
                        {
                            "id": "video-id",
                            "like_count": 6,
                            "comment_count": 2,
                            "share_count": 1,
                            "view_count": 50,
                        }
                    ]
                }
            }
        )
        refreshed = account._refresh_post_statistics(line)
        self.assertEqual(line.like_count, 6)
        self.assertEqual(line.comment_count, 2)
        self.assertEqual(line.share_count, 1)
        self.assertEqual(line.impression_count, 50)
        self.assertTrue(line.statistics_date)
        self.assertIn(line, refreshed)

    @patch(PATCH_POST)
    def test_action_post_publishes_and_registers_the_line(self, mock_post):
        """The publish flow reaches the connector and registers the line."""
        account = self._create_account()
        video = self.env["ir.attachment"].create(
            {"name": "test.mp4", "datas": "dGVzdA==", "mimetype": "video/mp4"}
        )
        post = self.env["social.post"].create(
            {
                "message": "Test post",
                "account_ids": [(4, account.id)],
                "video_ids": [(4, video.id)],
            }
        )

        def _post(url, **kwargs):
            if url.endswith("post/publish/video/init/"):
                return self._mock_response(
                    {
                        "data": {
                            "publish_id": "publish-id",
                            "upload_url": "https://upload.tiktok.com/video",
                        }
                    }
                )
            if url.endswith("post/publish/status/fetch/"):
                return self._mock_response(
                    {
                        "data": {
                            "status": "PUBLISH_COMPLETE",
                            "publicaly_available_post_id": ["video-id"],
                        }
                    }
                )
            raise AssertionError(f"unexpected call to {url}")

        mock_post.side_effect = _post
        with patch(PATCH_PUT, return_value=self._mock_response({})):
            post.action_create_post_account()
        line = post.post_account_ids
        self.assertEqual(line.state, "posted")
        self.assertEqual(line.remote_ref, "video-id")
        self.assertTrue(line.published_date)
        self.assertTrue(line.has_video)
        self.assertEqual(post.state, "published")


@tagged("post_install", "-at_install")
class TestSocialMediaTikTokController(HttpCase):
    """The endpoint TikTok calls when the user authorizes the app."""

    def test_callback_with_an_error_redirects(self):
        self.authenticate("admin", "admin")
        response = self.url_open(
            "/social_tiktok/callback?error=access_denied", allow_redirects=False
        )
        self.assertEqual(response.status_code, 303)

    @patch(
        "odoo.addons.social_media_tiktok.models.social_account."
        "SocialAccount.create_account_tiktok"
    )
    @patch(
        "odoo.addons.social_media_tiktok.models.social_account."
        "SocialAccount.get_access_token_tiktok",
        return_value=("key", "secret", {"access_token": "token"}),
    )
    def test_callback_links_the_account(self, mock_token, mock_create):
        self.authenticate("admin", "admin")
        response = self.url_open(
            "/social_tiktok/callback?code=code&state=state", allow_redirects=False
        )
        self.assertEqual(response.status_code, 303)
        mock_create.assert_called_once_with("key", "secret", {"access_token": "token"})

    @patch(
        "odoo.addons.social_media_tiktok.models.social_account."
        "SocialAccount.create_account_tiktok"
    )
    @patch(
        "odoo.addons.social_media_tiktok.models.social_account."
        "SocialAccount.get_access_token_tiktok",
        return_value=("key", "secret", {}),
    )
    def test_callback_without_tokens_redirects(self, mock_token, mock_create):
        self.authenticate("admin", "admin")
        response = self.url_open(
            "/social_tiktok/callback?code=code&state=state", allow_redirects=False
        )
        self.assertEqual(response.status_code, 303)
        mock_create.assert_not_called()

    @mute_logger("odoo.addons.social_media_tiktok.controllers.social_media_tiktok")
    @patch(
        "odoo.addons.social_media_tiktok.models.social_account."
        "SocialAccount.get_access_token_tiktok",
        side_effect=UserError("refused"),
    )
    def test_callback_with_a_failure_redirects(self, mock_token):
        self.authenticate("admin", "admin")
        response = self.url_open(
            "/social_tiktok/callback?code=code&state=state", allow_redirects=False
        )
        self.assertEqual(response.status_code, 303)
