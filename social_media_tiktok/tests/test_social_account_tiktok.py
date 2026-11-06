# Copyright 2026 Domatix <https://www.domatix.cloud>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import base64
from unittest.mock import patch

from odoo import fields
from odoo.exceptions import AccessError, UserError
from odoo.tools import mute_logger

from odoo.addons.social_media_base.exceptions import SocialCredentialsError

from .. import uninstall_hook
from .common import PNG_1X1, TikTokCommon

REQUESTS = "odoo.addons.social_media_tiktok.models.social_account.requests"
ACCOUNT = "odoo.addons.social_media_tiktok.models.social_account.SocialAccount"
LOGGER = "odoo.addons.social_media_tiktok.models.social_account"


class TestSocialAccountTikTok(TikTokCommon):
    """The TikTok calls of ``social.account``."""

    def test_uninstall_hook_clears_the_credentials(self):
        account = self._create_account()
        uninstall_hook(self.env)
        self.assertFalse(account.active)
        for field in (
            "tiktok_access_token",
            "tiktok_refresh_token",
            "tiktok_open_id",
            "tiktok_client_key",
            "tiktok_client_secret",
        ):
            self.assertFalse(account[field])

    def test_redirect_uri(self):
        self.assertTrue(
            self._create_account()
            ._tiktok_redirect_uri()
            .endswith("/social_tiktok/callback")
        )

    def test_get_removal_values(self):
        values = self._create_account()._get_removal_values()
        self.assertFalse(values["tiktok_access_token"])
        self.assertFalse(values["tiktok_refresh_token"])
        self.assertFalse(values["tiktok_token_expiration_date"])
        self.assertFalse(values["tiktok_open_id"])
        self.assertFalse(values["tiktok_client_key"])
        self.assertFalse(values["tiktok_client_secret"])

    def test_oauth_wizard_without_state(self):
        self.assertFalse(self._create_account()._get_tiktok_oauth_wizard(False))

    def test_oauth_wizard_matches_the_state(self):
        account = self._create_account()
        wizard = self._create_wizard(csrf_state_token="state-token")
        self.assertEqual(account._get_tiktok_oauth_wizard("state-token"), wizard)

    def test_consume_oauth_wizard_deletes_it(self):
        account = self._create_account()
        wizard = self._create_wizard(csrf_state_token="state-token")
        account._consume_tiktok_oauth_wizard("state-token")
        self.assertFalse(wizard.exists())

    @patch(f"{REQUESTS}.post")
    def test_access_token_refused(self, mock_post):
        self._create_wizard(
            tiktok_client_key="key",
            tiktok_client_secret="secret",
            csrf_state_token="state-token",
        )
        mock_post.return_value = self._response(None, 500, text="no token")
        with self.assertRaisesRegex(UserError, "no token"):
            self.env["social.account"].get_access_token_tiktok("code", "state-token")

    def test_create_account_without_a_token(self):
        with self.assertRaisesRegex(UserError, "no access token"):
            self.env["social.account"].create_account_tiktok("key", "secret", {})

    @patch(f"{ACCOUNT}._get_tiktok_user_info")
    def test_create_account(self, mock_info):
        mock_info.return_value = {
            "open_id": "open-id",
            "username": "created",
            "display_name": "Created",
            "follower_count": 3,
            "following_count": 2,
            "likes_count": 1,
            "video_count": 4,
        }
        self.env["social.account"].create_account_tiktok(
            "key",
            "secret",
            {"access_token": "token", "open_id": "open-id", "expires_in": 60},
        )
        account = self.env["social.account"].search(
            [("media_type", "=", "tiktok"), ("tiktok_open_id", "=", "open-id")]
        )
        self.assertEqual(account.name, "Created")
        self.assertEqual(account.follower_count, 3)
        self.assertEqual(account.video_count, 4)
        self.assertTrue(account.tiktok_token_expiration_date > fields.Datetime.now())

    @patch(f"{ACCOUNT}._get_tiktok_user_info")
    def test_create_account_updates_an_archived_one(self, mock_info):
        existing = self._create_account(remote_ref="open-id", active=False)
        mock_info.return_value = {"open_id": "open-id", "username": "again"}
        self.env["social.account"].create_account_tiktok(
            "key", "secret", {"access_token": "token", "open_id": "open-id"}
        )
        existing.invalidate_recordset()
        self.assertTrue(existing.active)
        self.assertEqual(existing.username, "again")

    @patch(f"{ACCOUNT}._get_tiktok_user_info")
    def test_create_account_updates_an_active_one(self, mock_info):
        existing = self._create_account(remote_ref="open-id")
        mock_info.return_value = {"open_id": "open-id", "username": "renamed"}
        self.env["social.account"].create_account_tiktok(
            "key", "secret", {"access_token": "token", "open_id": "open-id"}
        )
        existing.invalidate_recordset()
        self.assertTrue(existing.active)
        self.assertEqual(existing.username, "renamed")

    @patch(f"{ACCOUNT}._get_tiktok_user_info")
    def test_create_account_refuses_another_users_account(self, mock_info):
        self._create_account(remote_ref="open-id")
        mock_info.return_value = {"open_id": "open-id", "username": "again"}
        user = self._create_social_user("tiktok_other_user")
        with self.assertRaises(AccessError):
            self.env["social.account"].with_user(user).create_account_tiktok(
                "key", "secret", {"access_token": "token", "open_id": "open-id"}
            )

    @mute_logger(LOGGER)
    @patch(f"{REQUESTS}.get")
    def test_user_info_refused(self, mock_get):
        account = self._create_account()
        mock_get.return_value = self._response(None, 500, text="no user")
        self.assertEqual(account._get_tiktok_user_info("token"), {})

    @patch(f"{REQUESTS}.get")
    def test_user_info(self, mock_get):
        account = self._create_account()
        mock_get.return_value = self._response({"data": {"user": {"username": "x"}}})
        self.assertEqual(account._get_tiktok_user_info("token"), {"username": "x"})

    def test_token_is_valid(self):
        account = self._create_account()
        self.assertEqual(account._refresh_tiktok_token(), "access-token")

    def test_token_expired_without_refresh(self):
        account = self._create_account(
            tiktok_token_expiration_date="2000-01-01 00:00:00",
            tiktok_refresh_token=False,
        )
        with self.assertRaises(SocialCredentialsError):
            account._refresh_tiktok_token()

    @patch(f"{REQUESTS}.post")
    def test_token_refused_credentials(self, mock_post):
        account = self._create_account(tiktok_token_expiration_date="2000-01-01")
        mock_post.return_value = self._response(None, 401, text="expired")
        with self.assertRaises(SocialCredentialsError):
            account._refresh_tiktok_token()

    @patch(f"{REQUESTS}.post")
    def test_token_refresh_failed(self, mock_post):
        account = self._create_account(tiktok_token_expiration_date="2000-01-01")
        mock_post.return_value = self._response(None, 500, text="boom")
        with self.assertRaisesRegex(UserError, "boom"):
            account._refresh_tiktok_token()

    @patch(f"{REQUESTS}.post")
    def test_token_refresh_keeps_the_old_refresh_token(self, mock_post):
        account = self._create_account(tiktok_token_expiration_date="2000-01-01")
        mock_post.return_value = self._response({"access_token": "renewed"})
        account._refresh_tiktok_token()
        self.assertEqual(account.tiktok_refresh_token, "refresh-token")
        self.assertEqual(account.tiktok_access_token, "renewed")

    def test_validate_of_another_media(self):
        self.assertFalse(self.other_account.validate_access_token())

    def test_validate_renews_a_tiktok_token(self):
        account = self._create_account(tiktok_token_expiration_date="2000-01-01")
        with patch.object(type(account), "_refresh_tiktok_token") as mock_refresh:
            account.validate_access_token()
        mock_refresh.assert_called_once()

    def test_refresh_credentials_of_another_media(self):
        self.assertFalse(self.other_account._refresh_credentials())

    def test_refresh_credentials(self):
        account = self._create_account()
        self.assertTrue(account._refresh_credentials())

    @mute_logger(LOGGER)
    def test_refresh_credentials_failure(self):
        account = self._create_account()
        with patch.object(
            type(account),
            "_refresh_tiktok_token",
            side_effect=SocialCredentialsError("nope"),
        ):
            self.assertFalse(account._refresh_credentials())

    def test_account_data_of_another_media(self):
        self.assertFalse(self.other_account._update_account_data())

    @patch(f"{ACCOUNT}._get_tiktok_user_info", return_value={})
    def test_account_data_without_values(self, mock_info):
        account = self._create_account()
        account._update_account_data()
        self.assertEqual(account.name, "TikTok Test")

    @patch(f"{REQUESTS}.get")
    @patch(f"{ACCOUNT}._get_tiktok_user_info")
    def test_account_data_with_an_avatar(self, mock_info, mock_get):
        account = self._create_account()
        mock_info.return_value = {
            "username": "refreshed",
            "display_name": "Refreshed",
            "avatar_url": "https://cdn/avatar",
            "account_type": "BUSINESS",
        }
        mock_get.return_value = self._response(content=base64.b64decode(PNG_1X1))
        account._update_account_data()
        self.assertEqual(account.username, "refreshed")
        self.assertTrue(account.tiktok_avatar_url)

    @patch(f"{REQUESTS}.get")
    @patch(f"{ACCOUNT}._get_tiktok_user_info")
    def test_account_data_without_an_avatar(self, mock_info, mock_get):
        account = self._create_account()
        mock_info.return_value = {
            "username": "refreshed",
            "avatar_url": "https://cdn/avatar",
        }
        image_before = account.image_1920
        mock_get.return_value = self._response(None, 500)
        account._update_account_data()
        self.assertEqual(account.image_1920, image_before)

    def test_post_info(self):
        info = self._create_account()._tiktok_post_info("Title")
        self.assertEqual(info["title"], "Title")
        self.assertEqual(info["privacy_level"], "SELF_ONLY")
        self.assertFalse(info["disable_comment"])

    def test_post_without_a_video(self):
        account = self._create_account()
        line = self._create_line(account)
        with self.assertRaisesRegex(UserError, "require a video"):
            account._post_tiktok_video(line)

    @patch(f"{REQUESTS}.put")
    @patch(f"{REQUESTS}.post")
    def test_post(self, mock_post, mock_put):
        account = self._create_account()
        post = self._create_post(account, videos=self._video())
        line = self._create_line(account, post=post)
        mock_post.side_effect = [
            self._response(
                {"data": {"publish_id": "publish-id", "upload_url": "https://up"}}
            ),
            self._response(
                {
                    "data": {
                        "status": "PUBLISH_COMPLETE",
                        "publicaly_available_post_id": ["video-id"],
                    }
                }
            ),
        ]
        mock_put.return_value = self._response({})
        self.assertEqual(account._post_tiktok_video(line), "video-id")

    def test_post_without_a_publication_reference(self):
        account = self._create_account()
        post = self._create_post(account, videos=self._video())
        line = self._create_line(account, post=post)
        with patch.object(
            type(account), "_wait_for_tiktok_publication", return_value=False
        ):
            with patch(f"{REQUESTS}.put", return_value=self._response({})):
                with patch(
                    f"{REQUESTS}.post",
                    return_value=self._response(
                        {
                            "data": {
                                "publish_id": "publish-id",
                                "upload_url": "https://up",
                            }
                        }
                    ),
                ):
                    self.assertFalse(account._post_tiktok_video(line))

    @patch(f"{REQUESTS}.post")
    def test_initiate_refused_credentials(self, mock_post):
        account = self._create_account()
        post = self._create_post(account, videos=self._video())
        line = self._create_line(account, post=post)
        mock_post.return_value = self._response(None, 401, text="expired")
        with self.assertRaises(SocialCredentialsError):
            account._post_tiktok_video(line)

    @patch(f"{REQUESTS}.post")
    def test_initiate_refused_scope(self, mock_post):
        account = self._create_account()
        post = self._create_post(account, videos=self._video())
        line = self._create_line(account, post=post)
        mock_post.return_value = self._response(
            {"error": {"code": "scope_not_authorized"}}, status_code=403
        )
        with self.assertRaises(SocialCredentialsError):
            account._post_tiktok_video(line)

    @patch(f"{REQUESTS}.post")
    def test_initiate_refused_other(self, mock_post):
        account = self._create_account()
        post = self._create_post(account, videos=self._video())
        line = self._create_line(account, post=post)
        mock_post.return_value = self._response(
            {"error": {"code": "rate_limit"}}, status_code=403
        )
        with self.assertRaisesRegex(UserError, "refused the publication"):
            account._post_tiktok_video(line)

    @patch(f"{REQUESTS}.post")
    def test_initiate_failed(self, mock_post):
        account = self._create_account()
        post = self._create_post(account, videos=self._video())
        line = self._create_line(account, post=post)
        mock_post.return_value = self._response(None, 500, text="boom")
        with self.assertRaisesRegex(UserError, "initiation failed"):
            account._post_tiktok_video(line)

    @patch(f"{REQUESTS}.post")
    def test_initiate_without_upload_url(self, mock_post):
        account = self._create_account()
        post = self._create_post(account, videos=self._video())
        line = self._create_line(account, post=post)
        mock_post.return_value = self._response({"data": {}})
        with self.assertRaisesRegex(UserError, "no upload URL"):
            account._post_tiktok_video(line)

    def test_open_account_of_another_media(self):
        self.assertIsNone(self.other_media.action_open_account())

    @patch(f"{REQUESTS}.put")
    @patch(f"{REQUESTS}.post")
    def test_post_with_an_unknown_mimetype(self, mock_post, mock_put):
        account = self._create_account()
        video = self._video(mimetype="video/x-msvideo")
        post = self._create_post(account, videos=video)
        line = self._create_line(account, post=post)
        mock_post.side_effect = [
            self._response(
                {"data": {"publish_id": "publish-id", "upload_url": "https://up"}}
            ),
            self._response({"data": {"status": "PUBLISH_COMPLETE"}}),
        ]
        mock_put.return_value = self._response({})
        account._post_tiktok_video(line)
        headers = mock_put.call_args.kwargs["headers"]
        self.assertEqual(headers["Content-Type"], "video/mp4")

    @patch(f"{REQUESTS}.put")
    @patch(f"{REQUESTS}.post")
    def test_upload_in_chunks(self, mock_post, mock_put):
        account = self._create_account()
        post = self._create_post(account, videos=self._video(data=b"abcdef"))
        line = self._create_line(account, post=post)
        mock_post.side_effect = [
            self._response(
                {"data": {"publish_id": "publish-id", "upload_url": "https://up"}}
            ),
            self._response({"data": {"status": "PUBLISH_COMPLETE"}}),
        ]
        mock_put.return_value = self._response({})
        with patch(
            "odoo.addons.social_media_tiktok.models.social_account."
            "_MAX_CHUNK_SIZE_TIKTOK",
            3,
        ):
            account._post_tiktok_video(line)
        self.assertEqual(mock_put.call_count, 2)
        self.assertIn(
            "bytes 0-2/6", mock_put.call_args_list[0].kwargs["headers"]["Content-Range"]
        )
        self.assertIn(
            "bytes 3-5/6", mock_put.call_args_list[1].kwargs["headers"]["Content-Range"]
        )

    @patch(f"{REQUESTS}.put")
    @patch(f"{REQUESTS}.post")
    def test_upload_failed(self, mock_post, mock_put):
        account = self._create_account()
        post = self._create_post(account, videos=self._video())
        line = self._create_line(account, post=post)
        mock_post.return_value = self._response(
            {"data": {"publish_id": "publish-id", "upload_url": "https://up"}}
        )
        mock_put.return_value = self._response(None, 500, text="no upload")
        with self.assertRaisesRegex(UserError, "upload failed"):
            account._post_tiktok_video(line)

    @patch(f"{REQUESTS}.post")
    def test_wait_publication_published(self, mock_post):
        account = self._create_account()
        mock_post.return_value = self._response(
            {
                "data": {
                    "status": "PUBLISH_COMPLETE",
                    "publicaly_available_post_id": ["video-id"],
                }
            }
        )
        self.assertEqual(account._wait_for_tiktok_publication("publish-id"), "video-id")

    @patch(f"{REQUESTS}.post")
    def test_wait_publication_private(self, mock_post):
        account = self._create_account()
        mock_post.return_value = self._response(
            {"data": {"status": "SEND_TO_USER_INBOX"}}
        )
        self.assertFalse(account._wait_for_tiktok_publication("publish-id"))

    @patch(f"{REQUESTS}.post")
    def test_wait_publication_failed(self, mock_post):
        account = self._create_account()
        mock_post.return_value = self._response(
            {"data": {"status": "FAILED", "fail_reason": "bad video"}}
        )
        with self.assertRaisesRegex(UserError, "bad video"):
            account._wait_for_tiktok_publication("publish-id")

    @patch(f"{REQUESTS}.post")
    def test_wait_publication_refused_credentials(self, mock_post):
        account = self._create_account()
        mock_post.return_value = self._response(None, 403, text="expired")
        with self.assertRaises(SocialCredentialsError):
            account._wait_for_tiktok_publication("publish-id")

    @patch(f"{REQUESTS}.post")
    def test_wait_publication_refused(self, mock_post):
        account = self._create_account()
        mock_post.return_value = self._response(None, 500, text="no status")
        with self.assertRaisesRegex(UserError, "no status"):
            account._wait_for_tiktok_publication("publish-id")

    @patch(f"{REQUESTS}.post")
    def test_wait_publication_times_out(self, mock_post):
        account = self._create_account()
        mock_post.return_value = self._response({"data": {"status": "PROCESSING"}})
        with (
            patch("odoo.addons.social_media_tiktok.models.social_account.time.sleep"),
            self.assertRaisesRegex(UserError, "in time"),
        ):
            account._wait_for_tiktok_publication("publish-id")

    def test_delete_video_is_not_allowed(self):
        account = self._create_account()
        line = self._create_line(account, remote_ref="video-id")
        with self.assertRaisesRegex(UserError, "does not offer an API"):
            account._delete_tiktok_video(line)

    @mute_logger(LOGGER)
    @patch(f"{REQUESTS}.post")
    def test_video_list_refused(self, mock_post):
        account = self._create_account()
        mock_post.return_value = self._response(None, 500, text="no list")
        self.assertFalse(account._get_tiktok_videos())

    @patch(f"{REQUESTS}.post")
    def test_video_list(self, mock_post):
        account = self._create_account()
        mock_post.return_value = self._response({"data": {"videos": [{"id": "1"}]}})
        self.assertEqual(account._get_tiktok_videos(), [{"id": "1"}])

    @patch(f"{REQUESTS}.post")
    def test_statistics_leave_other_medias_alone(self, mock_post):
        account = self._create_account()
        line = self._create_line(self.other_account)
        self.assertFalse(account._refresh_post_statistics(line))
        mock_post.assert_not_called()

    @patch(f"{REQUESTS}.post")
    def test_statistics_refused(self, mock_post):
        account = self._create_account()
        line = self._create_line(account, remote_ref="video-id")
        mock_post.return_value = self._response(None, 500, text="no stats")
        with self.assertRaisesRegex(UserError, "no stats"):
            account._refresh_post_statistics(line)
