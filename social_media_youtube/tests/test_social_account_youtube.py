# Copyright 2026 Domatix <https://www.domatix.cloud>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from unittest.mock import patch

from odoo import fields
from odoo.exceptions import AccessError, UserError
from odoo.tools import mute_logger

from odoo.addons.social_media_base.exceptions import SocialCredentialsError

from .. import uninstall_hook
from .common import YouTubeCommon

REQUESTS = "odoo.addons.social_media_youtube.models.social_account.requests"
ACCOUNT = "odoo.addons.social_media_youtube.models.social_account.SocialAccount"
LOGGER = "odoo.addons.social_media_youtube.models.social_account"


class TestSocialAccountYouTube(YouTubeCommon):
    """The YouTube calls of ``social.account``."""

    def test_uninstall_hook_clears_the_credentials(self):
        account = self._create_account()
        uninstall_hook(self.env)
        self.assertFalse(account.active)
        for field in (
            "youtube_access_token",
            "youtube_refresh_token",
            "youtube_channel_id",
            "youtube_client_id",
            "youtube_client_secret",
        ):
            self.assertFalse(account[field])

    def test_open_account_of_another_media(self):
        self.assertIsNone(self.other_media.action_open_account())

    def test_redirect_uri(self):
        self.assertTrue(
            self._create_account()
            ._youtube_redirect_uri()
            .endswith("/social_youtube/callback")
        )

    def test_fields_account_url_without_channel(self):
        account = self._create_account(youtube_channel_id=False)
        self.assertNotIn("youtube", dict(account._fields_account_url()))

    def test_fields_account_url(self):
        account = self._create_account()
        self.assertEqual(
            dict(account._fields_account_url())["youtube"],
            "https://www.youtube.com/channel/channel-id",
        )

    def test_get_removal_values(self):
        values = self._create_account()._get_removal_values()
        self.assertFalse(values["youtube_access_token"])
        self.assertFalse(values["youtube_refresh_token"])
        self.assertFalse(values["youtube_token_expiration_date"])
        self.assertFalse(values["youtube_channel_id"])
        self.assertFalse(values["youtube_client_id"])
        self.assertFalse(values["youtube_client_secret"])

    def test_oauth_wizard_without_state(self):
        self.assertFalse(self._create_account()._get_youtube_oauth_wizard(False))

    def test_oauth_wizard_matches_the_state(self):
        account = self._create_account()
        wizard = self._create_wizard(csrf_state_token="state-token")
        self.assertEqual(account._get_youtube_oauth_wizard("state-token"), wizard)

    def test_consume_oauth_wizard_deletes_it(self):
        account = self._create_account()
        wizard = self._create_wizard(csrf_state_token="state-token")
        account._consume_youtube_oauth_wizard("state-token")
        self.assertFalse(wizard.exists())

    @patch(f"{REQUESTS}.post")
    def test_access_token_refused(self, mock_post):
        self._create_wizard(
            youtube_client_id="client-id",
            youtube_client_secret="client-secret",
            csrf_state_token="state-token",
        )
        mock_post.return_value = self._response(None, 500, text="no token")
        with self.assertRaisesRegex(UserError, "no token"):
            self.env["social.account"].get_access_token_youtube("code", "state-token")

    def test_create_account_without_a_token(self):
        with self.assertRaisesRegex(UserError, "no access token"):
            self.env["social.account"].create_youtube_account("id", "secret", {})

    @patch(f"{ACCOUNT}._get_youtube_channel", return_value={})
    def test_create_account_without_a_channel(self, mock_channel):
        with self.assertRaisesRegex(UserError, "Could not find any YouTube channel"):
            self.env["social.account"].create_youtube_account(
                "id", "secret", {"access_token": "token"}
            )

    @patch(f"{ACCOUNT}._get_youtube_channel")
    def test_create_account(self, mock_channel):
        mock_channel.return_value = {"id": "channel-id", "title": "Channel"}
        self.env["social.account"].create_youtube_account(
            "client-id", "client-secret", {"access_token": "token", "expires_in": 60}
        )
        account = self.env["social.account"].search(
            [("media_type", "=", "youtube"), ("youtube_channel_id", "=", "channel-id")]
        )
        self.assertEqual(account.name, "Channel")
        self.assertEqual(account.youtube_access_token, "token")
        self.assertTrue(account.youtube_token_expiration_date > fields.Datetime.now())

    @patch(f"{ACCOUNT}._get_youtube_channel")
    def test_create_account_updates_an_archived_one(self, mock_channel):
        existing = self._create_account(remote_ref="channel-id", active=False)
        mock_channel.return_value = {"id": "channel-id", "title": "Again"}
        self.env["social.account"].create_youtube_account(
            "client-id", "client-secret", {"access_token": "token"}
        )
        existing.invalidate_recordset()
        self.assertTrue(existing.active)
        self.assertEqual(existing.name, "Again")

    @patch(f"{ACCOUNT}._get_youtube_channel")
    def test_create_account_updates_an_active_one(self, mock_channel):
        existing = self._create_account(remote_ref="channel-id")
        mock_channel.return_value = {"id": "channel-id", "title": "Renamed"}
        self.env["social.account"].create_youtube_account(
            "client-id", "client-secret", {"access_token": "token"}
        )
        existing.invalidate_recordset()
        self.assertEqual(existing.name, "Renamed")

    @patch(f"{ACCOUNT}._get_youtube_channel")
    def test_create_account_refuses_another_users_channel(self, mock_channel):
        self._create_account(remote_ref="channel-id")
        mock_channel.return_value = {"id": "channel-id", "title": "Again"}
        user = self._create_social_user("youtube_other_user")
        with self.assertRaises(AccessError):
            self.env["social.account"].with_user(user).create_youtube_account(
                "client-id", "client-secret", {"access_token": "token"}
            )

    @mute_logger(LOGGER)
    @patch(f"{REQUESTS}.get")
    def test_channel_refused(self, mock_get):
        account = self._create_account()
        mock_get.return_value = self._response(None, 500, text="no channel")
        self.assertEqual(account._get_youtube_channel("token"), {})

    @patch(f"{REQUESTS}.get")
    def test_channel(self, mock_get):
        account = self._create_account()
        mock_get.return_value = self._response({"items": [{"id": "channel-id"}]})
        self.assertEqual(account._get_youtube_channel("token"), {"id": "channel-id"})

    @patch(f"{REQUESTS}.get")
    def test_channel_without_items(self, mock_get):
        account = self._create_account()
        mock_get.return_value = self._response({"items": []})
        self.assertEqual(account._get_youtube_channel("token"), {})

    def test_token_is_valid(self):
        self.assertEqual(
            self._create_account()._refresh_youtube_token(), "access-token"
        )

    def test_token_expired_without_refresh(self):
        account = self._create_account(
            youtube_token_expiration_date="2000-01-01 00:00:00",
            youtube_refresh_token=False,
        )
        with self.assertRaises(SocialCredentialsError):
            account._refresh_youtube_token()

    @patch(f"{REQUESTS}.post")
    def test_token_refused_credentials(self, mock_post):
        account = self._create_account(youtube_token_expiration_date="2000-01-01")
        mock_post.return_value = self._response(None, 400, text="expired")
        with self.assertRaises(SocialCredentialsError):
            account._refresh_youtube_token()

    @patch(f"{REQUESTS}.post")
    def test_token_refresh_failed(self, mock_post):
        account = self._create_account(youtube_token_expiration_date="2000-01-01")
        mock_post.return_value = self._response(None, 500, text="boom")
        with self.assertRaisesRegex(UserError, "boom"):
            account._refresh_youtube_token()

    @patch(f"{REQUESTS}.post")
    def test_token_refresh(self, mock_post):
        account = self._create_account(youtube_token_expiration_date="2000-01-01")
        mock_post.return_value = self._response({"access_token": "renewed"})
        self.assertEqual(account._refresh_youtube_token(), "renewed")
        self.assertEqual(account.youtube_access_token, "renewed")

    def test_validate_of_another_media(self):
        self.assertFalse(self.other_account.validate_access_token())

    def test_validate_renews_a_youtube_token(self):
        account = self._create_account(youtube_token_expiration_date="2000-01-01")
        with patch.object(type(account), "_refresh_youtube_token") as mock_refresh:
            account.validate_access_token()
        mock_refresh.assert_called_once()

    def test_refresh_credentials_of_another_media(self):
        self.assertFalse(self.other_account._refresh_credentials())

    def test_refresh_credentials(self):
        self.assertTrue(self._create_account()._refresh_credentials())

    @mute_logger(LOGGER)
    def test_refresh_credentials_failure(self):
        account = self._create_account()
        with patch.object(
            type(account),
            "_refresh_youtube_token",
            side_effect=SocialCredentialsError("nope"),
        ):
            self.assertFalse(account._refresh_credentials())

    def test_account_data_of_another_media(self):
        self.assertFalse(self.other_account._update_account_data())

    @patch(f"{ACCOUNT}._get_youtube_channel", return_value={})
    def test_account_data_without_a_channel(self, mock_channel):
        account = self._create_account()
        account._update_account_data()
        self.assertEqual(account.name, "YouTube Test")

    @patch(f"{ACCOUNT}._get_youtube_channel")
    def test_account_data(self, mock_channel):
        account = self._create_account()
        mock_channel.return_value = {
            "title": "Renamed",
            "statistics": {"subscriberCount": "42"},
        }
        account._update_account_data()
        self.assertEqual(account.name, "Renamed")
        self.assertEqual(account.follower_count, 42)

    def test_post_without_a_video(self):
        account = self._create_account()
        line = self._create_line(account)
        with self.assertRaisesRegex(UserError, "require a video"):
            account._post_youtube_video(line)

    @patch(f"{REQUESTS}.put")
    @patch(f"{REQUESTS}.post")
    def test_post(self, mock_post, mock_put):
        account = self._create_account()
        post = self._create_post(account, videos=self._video())
        line = self._create_line(account, post=post)
        mock_post.return_value = self._response(
            {}, headers={"Location": "https://upload.youtube"}
        )
        mock_put.return_value = self._response({"id": "video-id"})
        self.assertEqual(account._post_youtube_video(line), "video-id")

    @patch(f"{REQUESTS}.post")
    def test_post_refused_credentials(self, mock_post):
        account = self._create_account()
        post = self._create_post(account, videos=self._video())
        line = self._create_line(account, post=post)
        mock_post.return_value = self._response(None, 401, text="expired")
        with self.assertRaises(SocialCredentialsError):
            account._post_youtube_video(line)

    @patch(f"{REQUESTS}.post")
    def test_post_without_upload_url(self, mock_post):
        account = self._create_account()
        post = self._create_post(account, videos=self._video())
        line = self._create_line(account, post=post)
        mock_post.return_value = self._response({}, text="no upload")
        with self.assertRaisesRegex(UserError, "initiation failed"):
            account._post_youtube_video(line)

    @patch(f"{REQUESTS}.put")
    @patch(f"{REQUESTS}.post")
    def test_upload_failed(self, mock_post, mock_put):
        account = self._create_account()
        post = self._create_post(account, videos=self._video())
        line = self._create_line(account, post=post)
        mock_post.return_value = self._response(
            {}, headers={"Location": "https://upload.youtube"}
        )
        mock_put.return_value = self._response(None, 500, text="no upload")
        with self.assertRaisesRegex(UserError, "upload failed"):
            account._post_youtube_video(line)

    @patch(f"{REQUESTS}.put")
    @patch(f"{REQUESTS}.post")
    def test_title_is_cleaned(self, mock_post, mock_put):
        account = self._create_account()
        post = self._create_post(account, message="<b>Title</b>", videos=self._video())
        line = self._create_line(account, post=post, message="<b>Title</b>")
        mock_post.return_value = self._response(
            {}, headers={"Location": "https://upload.youtube"}
        )
        mock_put.return_value = self._response({"id": "video-id"})
        account._post_youtube_video(line)
        self.assertEqual(
            mock_post.call_args.kwargs["json"]["snippet"]["title"], "bTitle/b"
        )

    def test_delete_video_without_a_reference(self):
        account = self._create_account()
        line = self._create_line(account)
        self.assertEqual(
            account._delete_youtube_video(line), {"success": True, "message": ""}
        )

    @patch(f"{REQUESTS}.delete")
    def test_delete_video(self, mock_delete):
        account = self._create_account()
        line = self._create_line(account, remote_ref="video-id")
        mock_delete.return_value = self._response({}, status_code=204)
        self.assertTrue(account._delete_youtube_video(line)["success"])

    @patch(f"{REQUESTS}.delete")
    def test_delete_video_refused(self, mock_delete):
        account = self._create_account()
        line = self._create_line(account, remote_ref="video-id")
        mock_delete.return_value = self._response(None, 500, text="no delete")
        with self.assertRaisesRegex(UserError, "no delete"):
            account._delete_youtube_video(line)

    @patch(f"{REQUESTS}.get")
    def test_statistics_leave_other_medias_alone(self, mock_get):
        account = self._create_account()
        line = self._create_line(self.other_account)
        self.assertFalse(account._refresh_post_statistics(line))
        mock_get.assert_not_called()

    @patch(f"{REQUESTS}.get")
    def test_statistics(self, mock_get):
        account = self._create_account()
        line = self._create_line(account, remote_ref="video-id")
        mock_get.return_value = self._response(
            {
                "items": [
                    {
                        "id": "video-id",
                        "statistics": {
                            "likeCount": "5",
                            "commentCount": "2",
                            "viewCount": "100",
                        },
                    }
                ]
            }
        )
        refreshed = account._refresh_post_statistics(line)
        self.assertEqual(line.like_count, 5)
        self.assertEqual(line.comment_count, 2)
        self.assertEqual(line.impression_count, 100)
        self.assertIn(line, refreshed)

    @patch(f"{REQUESTS}.get")
    def test_statistics_refused(self, mock_get):
        account = self._create_account()
        line = self._create_line(account, remote_ref="video-id")
        mock_get.return_value = self._response(None, 500, text="no stats")
        with self.assertRaisesRegex(UserError, "no stats"):
            account._refresh_post_statistics(line)
