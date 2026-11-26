# Copyright 2026 Domatix <https://www.domatix.cloud>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from unittest.mock import MagicMock, patch
from urllib.parse import parse_qs, urlparse

from odoo.exceptions import UserError
from odoo.tests import HttpCase, TransactionCase, tagged
from odoo.tools import mute_logger

PATCH_POST = "odoo.addons.social_media_youtube.models.social_account.requests.post"
PATCH_GET = "odoo.addons.social_media_youtube.models.social_account.requests.get"
PATCH_PUT = "odoo.addons.social_media_youtube.models.social_account.requests.put"
PATCH_POST_ACCOUNT_GET = (
    "odoo.addons.social_media_youtube.models.social_post_account.requests.get"
)


class TestSocialMediaYouTube(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.media = cls.env.ref("social_media_youtube.social_media_youtube")
        cls.user = cls.env.user

    def _create_account(self):
        return self.env["social.account"].create(
            {
                "name": "YouTube Test",
                "media_id": self.media.id,
                "user_id": self.user.id,
                "youtube_channel_id": "channel-id",
                "youtube_access_token": "access-token",
                "youtube_refresh_token": "refresh-token",
                "youtube_token_expiration_date": "2099-01-01 00:00:00",
                "youtube_client_id": "client-id",
                "youtube_client_secret": "client-secret",
            }
        )

    def _mock_response(self, json_data, status_code=200):
        response = MagicMock()
        response.status_code = status_code
        response.json.return_value = json_data
        return response

    def test_media_registered(self):
        self.assertEqual(self.media.media_type, "youtube")

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
                "youtube_client_id": "client-id",
                "youtube_client_secret": "client-secret",
            }
        )
        action = wizard.action_associate_social_account()
        self.assertEqual(action["type"], "ir.actions.act_url")
        self.assertIn("accounts.google.com", action["url"])
        redirect_uri = parse_qs(urlparse(action["url"]).query)["redirect_uri"][0]
        self.assertTrue(redirect_uri.endswith("/social_youtube/callback"))

    def test_get_access_token_youtube_invalid_state(self):
        with self.assertRaises(UserError):
            self.env["social.account"].get_access_token_youtube("code", "bad-state")

    @patch(PATCH_POST)
    def test_get_access_token_youtube(self, mock_post):
        self.env["wizard.social.account"].create(
            {
                "media_id": self.media.id,
                "youtube_client_id": "client-id",
                "youtube_client_secret": "client-secret",
                "csrf_state_token": "state-token",
            }
        )
        mock_post.return_value = self._mock_response({"access_token": "new-token"})
        client_id, client_secret, tokens = self.env[
            "social.account"
        ].get_access_token_youtube("code", "state-token")
        self.assertEqual(client_id, "client-id")
        self.assertEqual(client_secret, "client-secret")
        self.assertEqual(tokens["access_token"], "new-token")

    @patch(PATCH_POST)
    def test_refresh_youtube_token(self, mock_post):
        account = self._create_account()
        account.youtube_token_expiration_date = "2000-01-01 00:00:00"
        mock_post.return_value = self._mock_response(
            {"access_token": "refreshed-token", "expires_in": 3600}
        )
        token = account._refresh_youtube_token()
        self.assertEqual(token, "refreshed-token")
        self.assertEqual(account.youtube_access_token, "refreshed-token")

    def test_fields_account_url_empty(self):
        account = self._create_account()
        account.youtube_channel_id = False
        urls = dict(account._fields_account_url())
        self.assertNotIn("youtube", urls)

    def test_fields_account_url(self):
        account = self._create_account()
        urls = dict(account._fields_account_url())
        self.assertEqual(urls["youtube"], "https://www.youtube.com/channel/channel-id")

    @patch(PATCH_POST_ACCOUNT_GET)
    def test_get_comments(self, mock_get):
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
        post_account = self.env["social.post.account"].create(
            {
                "post_id": post.id,
                "account_id": account.id,
                "media_id": self.media.id,
                "message": "Test post",
            }
        )
        mock_get.return_value = self._mock_response(
            {
                "items": [
                    {
                        "snippet": {
                            "topLevelComment": {
                                "id": "comment-id",
                                "snippet": {
                                    "textDisplay": "Nice video",
                                    "authorDisplayName": "Viewer",
                                },
                            }
                        }
                    }
                ]
            }
        )
        result = post_account.get_comments()
        self.assertTrue(result["success"])
        self.assertEqual(result["data"][0]["text"], "Nice video")

    @patch(PATCH_GET)
    def test_refresh_post_statistics(self, mock_get):
        """The counters YouTube reports land on the publication."""
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
        mock_get.return_value = self._mock_response(
            {
                "items": [
                    {
                        "id": "video-id",
                        "statistics": {
                            "likeCount": "4",
                            "commentCount": "1",
                            "viewCount": "100",
                        },
                    }
                ]
            }
        )
        refreshed = account._refresh_post_statistics(line)
        self.assertEqual(line.like_count, 4)
        self.assertEqual(line.comment_count, 1)
        self.assertEqual(line.impression_count, 100)
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
        initiate = self._mock_response({})
        initiate.headers = {"Location": "https://upload.youtube.com/session"}
        mock_post.return_value = initiate
        with patch(
            PATCH_PUT, return_value=self._mock_response({"id": "youtube-video-id"})
        ):
            post.action_create_post_account()
        line = post.post_account_ids
        self.assertEqual(line.state, "posted")
        self.assertEqual(line.remote_ref, "youtube-video-id")
        self.assertTrue(line.published_date)
        self.assertTrue(line.has_video)
        self.assertEqual(
            line.post_account_url,
            "https://www.youtube.com/watch?v=youtube-video-id",
        )
        self.assertEqual(post.state, "published")
        self.assertEqual(
            mock_post.call_args.kwargs["json"]["status"]["privacyStatus"], "private"
        )

    @patch(PATCH_POST)
    def test_action_post_sends_the_privacy_of_the_post(self, mock_post):
        """The visibility chosen on the post is the one sent to YouTube."""
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
        post.youtube_privacy_status = "unlisted"
        initiate = self._mock_response({})
        initiate.headers = {"Location": "https://upload.youtube.com/session"}
        mock_post.return_value = initiate
        with patch(
            PATCH_PUT, return_value=self._mock_response({"id": "youtube-video-id"})
        ):
            post.action_create_post_account()
        self.assertEqual(
            mock_post.call_args.kwargs["json"]["status"]["privacyStatus"], "unlisted"
        )


@tagged("post_install", "-at_install")
class TestSocialMediaYouTubeController(HttpCase):
    """The endpoint Google calls when the user authorizes the app."""

    def test_callback_with_an_error_redirects(self):
        self.authenticate("admin", "admin")
        response = self.url_open(
            "/social_youtube/callback?error=access_denied", allow_redirects=False
        )
        self.assertEqual(response.status_code, 303)

    @patch(
        "odoo.addons.social_media_youtube.models.social_account."
        "SocialAccount.create_youtube_account"
    )
    @patch(
        "odoo.addons.social_media_youtube.models.social_account."
        "SocialAccount.get_access_token_youtube",
        return_value=("client-id", "client-secret", {"access_token": "token"}),
    )
    def test_callback_links_the_account(self, mock_token, mock_create):
        self.authenticate("admin", "admin")
        response = self.url_open(
            "/social_youtube/callback?code=code&state=state", allow_redirects=False
        )
        self.assertEqual(response.status_code, 303)
        mock_create.assert_called_once_with(
            "client-id", "client-secret", {"access_token": "token"}
        )

    @patch(
        "odoo.addons.social_media_youtube.models.social_account."
        "SocialAccount.create_youtube_account"
    )
    @patch(
        "odoo.addons.social_media_youtube.models.social_account."
        "SocialAccount.get_access_token_youtube",
        return_value=("client-id", "client-secret", {}),
    )
    def test_callback_without_tokens_redirects(self, mock_token, mock_create):
        self.authenticate("admin", "admin")
        response = self.url_open(
            "/social_youtube/callback?code=code&state=state", allow_redirects=False
        )
        self.assertEqual(response.status_code, 303)
        mock_create.assert_not_called()

    @mute_logger("odoo.addons.social_media_youtube.controllers.social_media_youtube")
    @patch(
        "odoo.addons.social_media_youtube.models.social_account."
        "SocialAccount.get_access_token_youtube",
        side_effect=UserError("refused"),
    )
    def test_callback_with_a_failure_redirects(self, mock_token):
        self.authenticate("admin", "admin")
        response = self.url_open(
            "/social_youtube/callback?code=code&state=state", allow_redirects=False
        )
        self.assertEqual(response.status_code, 303)
