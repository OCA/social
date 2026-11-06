# Copyright 2026 Domatix <https://www.domatix.cloud>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from datetime import timedelta
from unittest.mock import MagicMock, patch

from odoo import fields
from odoo.exceptions import AccessError, UserError
from odoo.tools import mute_logger

from odoo.addons.social_media_base.exceptions import SocialCredentialsError

from .. import uninstall_hook
from .common import PNG_1X1, InstagramCommon

REQUESTS = "odoo.addons.social_media_instagram.models.social_account.requests"
ACCOUNT = "odoo.addons.social_media_instagram.models.social_account.SocialAccount"
LOGGER = "odoo.addons.social_media_instagram.models.social_account"


class TestSocialAccountInstagram(InstagramCommon):
    """The Instagram calls of ``social.account``."""

    def test_uninstall_hook_clears_the_credentials(self):
        account = self._create_account()
        uninstall_hook(self.env)
        self.assertFalse(account.active)
        for field in (
            "instagram_access_token",
            "instagram_account_id",
            "instagram_app_id",
            "instagram_app_secret",
        ):
            self.assertFalse(account[field])

    def test_redirect_uri(self):
        account = self._create_account()
        self.assertTrue(
            account._instagram_redirect_uri().endswith("/social_instagram/callback")
        )

    def test_get_removal_values(self):
        values = self._create_account()._get_removal_values()
        self.assertFalse(values["instagram_access_token"])
        self.assertFalse(values["instagram_account_id"])
        self.assertFalse(values["instagram_app_id"])
        self.assertFalse(values["instagram_app_secret"])

    def test_oauth_wizard_without_state(self):
        self.assertFalse(self._create_account()._get_instagram_oauth_wizard(False))

    def test_oauth_wizard_matches_the_state(self):
        account = self._create_account()
        wizard = self._create_wizard(csrf_state_token="state-token")
        self.assertEqual(account._get_instagram_oauth_wizard("state-token"), wizard)

    def test_consume_oauth_wizard_deletes_it(self):
        account = self._create_account()
        wizard = self._create_wizard(csrf_state_token="state-token")
        account._consume_instagram_oauth_wizard("state-token")
        self.assertFalse(wizard.exists())

    @patch(f"{REQUESTS}.post")
    def test_access_token_refused(self, mock_post):
        self._create_wizard(
            instagram_app_id="app-id",
            instagram_app_secret="app-secret",
            csrf_state_token="state-token",
        )
        mock_post.return_value = self._response(None, 500, text="no token")
        with self.assertRaisesRegex(UserError, "no token"):
            self.env["social.account"].get_access_token_instagram("code", "state-token")

    @patch(f"{REQUESTS}.post")
    def test_access_token_without_a_token(self, mock_post):
        self._create_wizard(
            instagram_app_id="app-id",
            instagram_app_secret="app-secret",
            csrf_state_token="state-token",
        )
        mock_post.return_value = self._response({"user_id": "1"})
        with self.assertRaisesRegex(UserError, "without an access token"):
            self.env["social.account"].get_access_token_instagram("code", "state-token")

    @patch(f"{REQUESTS}.get")
    @patch(f"{REQUESTS}.post")
    def test_access_token_from_the_data_shape(self, mock_post, mock_get):
        self._create_wizard(
            instagram_app_id="app-id",
            instagram_app_secret="app-secret",
            csrf_state_token="state-token",
        )
        mock_post.return_value = self._response(
            {"data": [{"access_token": "nested-token"}]}
        )
        mock_get.return_value = self._response({"access_token": "long-lived"})
        _, _, token, _ = self.env["social.account"].get_access_token_instagram(
            "code", "state-token"
        )
        self.assertEqual(token, "long-lived")

    @patch(f"{REQUESTS}.get")
    @patch(f"{REQUESTS}.post")
    def test_long_lived_refused(self, mock_post, mock_get):
        self._create_wizard(
            instagram_app_id="app-id",
            instagram_app_secret="app-secret",
            csrf_state_token="state-token",
        )
        mock_post.return_value = self._response({"access_token": "short"})
        mock_get.return_value = self._response(None, 500, text="no exchange")
        with self.assertRaisesRegex(UserError, "no exchange"):
            self.env["social.account"].get_access_token_instagram("code", "state-token")

    @patch(f"{REQUESTS}.get")
    def test_refresh_token_refused_credentials(self, mock_get):
        account = self._create_account()
        mock_get.return_value = self._response(None, 401, text="expired")
        with self.assertRaises(SocialCredentialsError):
            account._refresh_instagram_token()

    @patch(f"{REQUESTS}.get")
    def test_refresh_token_failed(self, mock_get):
        account = self._create_account()
        mock_get.return_value = self._response(None, 500, text="boom")
        with self.assertRaisesRegex(UserError, "boom"):
            account._refresh_instagram_token()

    @patch(f"{REQUESTS}.get")
    def test_refresh_token_writes_the_new_dates(self, mock_get):
        account = self._create_account()
        mock_get.return_value = self._response(
            {"access_token": "renewed", "expires_in": 3600}
        )
        account._refresh_instagram_token()
        self.assertEqual(account.instagram_access_token, "renewed")
        self.assertEqual(
            account.expire_access_token_date,
            fields.Date.today() + timedelta(seconds=3600),
        )

    @patch(f"{REQUESTS}.get")
    def test_refresh_token_without_expiry(self, mock_get):
        account = self._create_account()
        mock_get.return_value = self._response({"access_token": "renewed"})
        self.assertEqual(account._refresh_instagram_token(), "renewed")
        self.assertFalse(account.expire_access_token_date)

    def test_validate_without_expiry(self):
        account = self._create_account()
        self.assertFalse(account.validate_access_token())

    def test_validate_far_from_expiry(self):
        account = self._create_account()
        account.expire_access_token_date = fields.Date.today() + timedelta(days=30)
        with patch.object(type(account), "_refresh_instagram_token") as mock_refresh:
            account.validate_access_token()
        mock_refresh.assert_not_called()

    def test_validate_near_expiry_renews(self):
        account = self._create_account()
        account.expire_access_token_date = fields.Date.today() + timedelta(days=1)
        with patch.object(type(account), "_refresh_instagram_token") as mock_refresh:
            account.validate_access_token()
        mock_refresh.assert_called_once()

    def test_validate_with_a_refresh_failure(self):
        account = self._create_account()
        account.expire_access_token_date = fields.Date.today() + timedelta(days=1)
        with patch.object(
            type(account),
            "_refresh_instagram_token",
            side_effect=UserError("nope"),
        ):
            with self.assertRaises(SocialCredentialsError):
                account.validate_access_token()

    def test_validate_of_another_media(self):
        self.assertFalse(self.other_account.validate_access_token())

    def test_refresh_credentials_of_another_media(self):
        self.assertFalse(self.other_account._refresh_credentials())

    def test_refresh_credentials(self):
        account = self._create_account()
        with patch.object(
            type(account), "_refresh_instagram_token", return_value="token"
        ):
            self.assertTrue(account._refresh_credentials())

    @mute_logger(LOGGER)
    def test_refresh_credentials_failure(self):
        account = self._create_account()
        with patch.object(
            type(account),
            "_refresh_instagram_token",
            side_effect=SocialCredentialsError("nope"),
        ):
            self.assertFalse(account._refresh_credentials())

    def test_check_response_accepts_a_success(self):
        self._create_account()._instagram_check_response(self._response({}), "Anything")

    def test_check_response_refused_credentials(self):
        account = self._create_account()
        with self.assertRaises(SocialCredentialsError):
            account._instagram_check_response(self._response(None, 401), "Anything")
        with self.assertRaises(SocialCredentialsError):
            account._instagram_check_response(self._response(None, 403), "Anything")
        with self.assertRaises(SocialCredentialsError):
            account._instagram_check_response(
                self._response({"error": {"code": 190}}, status_code=400), "Anything"
            )

    def test_check_response_plain_error(self):
        account = self._create_account()
        with self.assertRaises(UserError):
            account._instagram_check_response(
                self._response(None, 500, text="boom"), "Anything"
            )

    @patch(f"{REQUESTS}.get")
    def test_profile(self, mock_get):
        account = self._create_account()
        mock_get.return_value = self._response({"username": "testuser"})
        self.assertEqual(
            account._get_instagram_profile("token"), {"username": "testuser"}
        )

    @patch(f"{REQUESTS}.get")
    def test_profile_refused(self, mock_get):
        account = self._create_account()
        mock_get.return_value = self._response(None, 500, text="no profile")
        with self.assertRaisesRegex(UserError, "no profile"):
            account._get_instagram_profile("token")

    @patch(f"{REQUESTS}.get")
    def test_profile_image(self, mock_get):
        account = self._create_account()
        mock_get.return_value = self._response(content=b"picture")
        self.assertTrue(account._instagram_profile_image("https://cdn/picture"))

    @patch(f"{REQUESTS}.get")
    def test_profile_image_refused(self, mock_get):
        account = self._create_account()
        mock_get.return_value = self._response(None, 500)
        self.assertFalse(account._instagram_profile_image("https://cdn/picture"))

    def test_profile_image_without_url(self):
        self.assertFalse(self._create_account()._instagram_profile_image(False))

    @patch(f"{ACCOUNT}._instagram_profile_image", return_value=False)
    @patch(f"{ACCOUNT}._instagram_import_posts")
    @patch(f"{ACCOUNT}._get_instagram_profile")
    def test_create_account(self, mock_profile, mock_import, mock_image):
        mock_profile.return_value = {
            "id": "ig-user-id",
            "username": "created",
            "profile_picture_url": False,
        }
        self.env["social.account"].create_instagram_accounts(
            "app-id", "app-secret", "access-token", expires_in=600
        )
        account = self.env["social.account"].search(
            [
                ("media_type", "=", "instagram"),
                ("instagram_account_id", "=", "ig-user-id"),
            ]
        )
        self.assertEqual(account.username, "created")
        self.assertEqual(account.instagram_access_token, "access-token")
        self.assertEqual(
            account.expire_access_token_date,
            fields.Date.today() + timedelta(seconds=600),
        )
        mock_import.assert_called_once()

    @patch(f"{ACCOUNT}._instagram_profile_image", return_value=PNG_1X1)
    @patch(f"{ACCOUNT}._instagram_import_posts")
    @patch(f"{ACCOUNT}._get_instagram_profile")
    def test_create_account_with_a_picture(self, mock_profile, mock_import, mock_image):
        mock_profile.return_value = {"id": "ig-user-id", "username": "created"}
        self.env["social.account"].create_instagram_accounts("app", "secret", "token")
        account = self.env["social.account"].search(
            [("instagram_account_id", "=", "ig-user-id")]
        )
        self.assertTrue(account.image_1920)
        self.assertTrue(account)

    @patch(f"{ACCOUNT}._get_instagram_profile", return_value={"id": False})
    def test_create_account_without_a_profile_id(self, mock_profile):
        with self.assertRaisesRegex(UserError, "Could not find any Instagram account"):
            self.env["social.account"].create_instagram_accounts(
                "app", "secret", "token"
            )

    @patch(f"{ACCOUNT}._instagram_import_posts")
    @patch(f"{ACCOUNT}._instagram_profile_image", return_value=False)
    @patch(f"{ACCOUNT}._get_instagram_profile")
    def test_create_account_updates_an_archived_one(
        self, mock_profile, mock_image, mock_import
    ):
        existing = self._create_account(remote_ref="ig-user-id", active=False)
        mock_profile.return_value = {"id": "ig-user-id", "username": "again"}
        self.env["social.account"].create_instagram_accounts("app", "secret", "token")
        existing.invalidate_recordset()
        self.assertTrue(existing.active)
        self.assertEqual(existing.username, "again")

    @patch(f"{ACCOUNT}._instagram_import_posts")
    @patch(f"{ACCOUNT}._instagram_profile_image", return_value=False)
    @patch(f"{ACCOUNT}._get_instagram_profile")
    def test_create_account_updates_an_active_one(
        self, mock_profile, mock_image, mock_import
    ):
        existing = self._create_account(remote_ref="ig-user-id")
        mock_profile.return_value = {"id": "ig-user-id", "username": "renamed"}
        self.env["social.account"].create_instagram_accounts("app", "secret", "token")
        existing.invalidate_recordset()
        self.assertTrue(existing.active)
        self.assertEqual(existing.username, "renamed")

    @patch(f"{ACCOUNT}._instagram_import_posts")
    @patch(f"{ACCOUNT}._instagram_profile_image", return_value=False)
    @patch(f"{ACCOUNT}._get_instagram_profile")
    def test_create_account_refuses_another_users_page(
        self, mock_profile, mock_image, mock_import
    ):
        self._create_account(remote_ref="ig-user-id")
        mock_profile.return_value = {"id": "ig-user-id", "username": "again"}
        user = self._create_social_user("instagram_other_user")
        with self.assertRaises(AccessError):
            self.env["social.account"].with_user(user).create_instagram_accounts(
                "app", "secret", "token"
            )

    def test_import_without_a_token(self):
        account = self._create_account(instagram_access_token=False)
        self.assertFalse(account._instagram_import_posts())

    @patch(f"{REQUESTS}.get")
    def test_import_refused(self, mock_get):
        account = self._create_account()
        mock_get.return_value = self._response(None, 500, text="no feed")
        with self.assertRaisesRegex(UserError, "no feed"):
            account._instagram_import_posts()

    @patch(f"{ACCOUNT}._instagram_import_post")
    @patch(f"{REQUESTS}.get")
    def test_import_follows_pages(self, mock_get, mock_import):
        account = self._create_account()
        mock_get.side_effect = [
            self._response({"data": [{"id": "1"}], "paging": {"next": "https://next"}}),
            self._response({"data": [{"id": "2"}]}),
        ]
        mock_import.return_value = self.env["social.post.account"]
        account._instagram_import_posts()
        self.assertEqual(mock_import.call_count, 2)

    @patch(f"{ACCOUNT}._instagram_import_post")
    @patch(f"{REQUESTS}.get")
    def test_import_stops_at_the_maximum_pages(self, mock_get, mock_import):
        account = self._create_account()
        mock_get.side_effect = [
            self._response(
                {"data": [{"id": str(index)}], "paging": {"next": "https://next"}}
            )
            for index in range(5)
        ]
        mock_import.return_value = self.env["social.post.account"]
        account._instagram_import_posts()
        self.assertEqual(mock_get.call_count, 5)

    def test_post_is_imported_without_a_reference(self):
        self.assertFalse(self._create_account()._instagram_post_is_imported(False))

    def test_post_is_imported(self):
        account = self._create_account()
        self._create_line(account, remote_ref="imported")
        self.assertTrue(account._instagram_post_is_imported("imported"))
        self.assertFalse(account._instagram_post_is_imported("unknown"))

    def test_open_account_of_another_media(self):
        self.assertIsNone(self.other_media.action_open_account())

    def test_timestamp(self):
        account = self._create_account()
        self.assertFalse(account._instagram_timestamp(False))
        self.assertEqual(
            account._instagram_timestamp("2026-08-31T20:02:19+0000").year, 2026
        )

    @patch(f"{REQUESTS}.get")
    def test_children_follow_pages(self, mock_get):
        account = self._create_account()
        mock_get.side_effect = [
            self._response({"data": [{"id": "1"}], "paging": {"next": "https://next"}}),
            self._response({"data": [{"id": "2"}]}),
        ]
        children = account._instagram_children("parent", "token")
        self.assertEqual([child["id"] for child in children], ["1", "2"])

    @patch(f"{REQUESTS}.get")
    def test_children_refused(self, mock_get):
        account = self._create_account()
        mock_get.return_value = self._response(None, 500, text="no children")
        with self.assertRaisesRegex(UserError, "no children"):
            account._instagram_children("parent", "token")

    @patch(f"{REQUESTS}.get")
    def test_media_of_a_carousel(self, mock_get):
        account = self._create_account()
        mock_get.side_effect = [
            self._response(
                {
                    "data": [
                        {
                            "id": "1",
                            "media_type": "IMAGE",
                            "media_url": "https://cdn/1",
                        },
                        {
                            "id": "2",
                            "media_type": "VIDEO",
                            "thumbnail_url": "https://cdn/2",
                        },
                    ]
                }
            ),
            self._response(content=b"image"),
            self._response(content=b"cover"),
        ]
        media = account._instagram_media_attachments(
            {"id": "carousel", "media_type": "CAROUSEL_ALBUM"}, "token"
        )
        self.assertEqual(len(media["images"]), 2)
        self.assertTrue(media["refs"])

    @patch(f"{REQUESTS}.get")
    def test_media_of_a_carousel_with_a_video_child(self, mock_get):
        account = self._create_account()
        mock_get.side_effect = [
            self._response(
                {
                    "data": [
                        {
                            "id": "child-1",
                            "media_type": "VIDEO",
                            "thumbnail_url": "https://cdn/cover.jpg",
                        }
                    ]
                }
            ),
            self._response(content=b"cover"),
        ]
        media = account._instagram_media_attachments(
            {"id": "carousel", "media_type": "CAROUSEL_ALBUM"}, "token"
        )
        self.assertEqual(len(media["images"]), 1)

    @patch(f"{REQUESTS}.get")
    def test_media_of_an_unavailable_child(self, mock_get):
        account = self._create_account()
        mock_get.side_effect = [
            self._response({"data": [{"id": "child-1", "media_type": "IMAGE"}]}),
        ]
        media = account._instagram_media_attachments(
            {"id": "carousel", "media_type": "CAROUSEL_ALBUM"}, "token"
        )
        self.assertFalse(media["images"])

    @patch(f"{REQUESTS}.get")
    def test_media_of_an_image(self, mock_get):
        account = self._create_account()
        mock_get.return_value = self._response(content=b"image")
        media = account._instagram_media_attachments(
            {"id": "image", "media_type": "IMAGE", "media_url": "https://cdn/image"},
            "token",
        )
        self.assertEqual(len(media["images"]), 1)

    @patch(f"{REQUESTS}.get")
    def test_media_of_a_video(self, mock_get):
        account = self._create_account()
        mock_get.return_value = self._response(content=b"cover")
        media = account._instagram_media_attachments(
            {
                "id": "video",
                "media_type": "VIDEO",
                "thumbnail_url": "https://cdn/cover",
            },
            "token",
        )
        self.assertEqual(len(media["images"]), 1)

    @patch(f"{REQUESTS}.get")
    def test_media_of_a_carousel_without_the_child(self, mock_get):
        account = self._create_account()
        mock_get.side_effect = [
            self._response(
                {
                    "data": [
                        {"id": "1", "media_type": "IMAGE", "media_url": "https://cdn/1"}
                    ]
                }
            ),
            self._response(None, 500),
        ]
        media = account._instagram_media_attachments(
            {"id": "carousel", "media_type": "CAROUSEL_ALBUM"}, "token"
        )
        self.assertFalse(media["images"])

    @patch(f"{REQUESTS}.get")
    def test_media_of_an_image_that_fails(self, mock_get):
        account = self._create_account()
        mock_get.return_value = self._response(None, 500)
        media = account._instagram_media_attachments(
            {"id": "image", "media_type": "IMAGE", "media_url": "https://cdn/image"},
            "token",
        )
        self.assertFalse(media["images"])

    @patch(f"{REQUESTS}.get")
    def test_media_of_a_video_that_fails(self, mock_get):
        account = self._create_account()
        mock_get.return_value = self._response(None, 500)
        media = account._instagram_media_attachments(
            {
                "id": "video",
                "media_type": "VIDEO",
                "thumbnail_url": "https://cdn/cover",
            },
            "token",
        )
        self.assertFalse(media["images"])

    @patch(f"{REQUESTS}.get")
    def test_download_refused(self, mock_get):
        account = self._create_account()
        mock_get.return_value = self._response(None, 500)
        self.assertFalse(account._instagram_download("name", "https://cdn/file"))

    def test_download_without_url(self):
        self.assertFalse(self._create_account()._instagram_download("name", False))

    @patch(
        "odoo.addons.social_media_base.models.social_account."
        "SocialAccount._refresh_account_statistics",
        return_value=None,
    )
    @patch(
        "odoo.addons.social_media_base.models.social_account."
        "SocialAccount._refresh_window_statistics",
        return_value=None,
    )
    @patch(
        "odoo.addons.social_media_base.models.social_account."
        "SocialAccount._refresh_statistics",
        return_value=None,
    )
    @patch(f"{ACCOUNT}._instagram_import_posts")
    def test_refresh_dashboard_statistics_imports_the_feed(
        self, mock_import, mock_statistics, mock_window, mock_account
    ):
        account = self._create_account()
        account.refresh_dashboard_statistics()
        mock_import.assert_called_once()

    @patch(f"{ACCOUNT}._instagram_import_posts")
    def test_check_media_updates_imports_the_feed(self, mock_import):
        mock_import.return_value = self.env["social.post.account"]
        self._create_account()
        self.env["social.account"]._run_check_media_updates()
        mock_import.assert_called_once()

    def test_account_data_of_another_media(self):
        self.assertFalse(self.other_account._update_account_data())

    @patch(f"{ACCOUNT}._get_instagram_profile", return_value={})
    @patch(f"{ACCOUNT}._instagram_profile_image", return_value=False)
    def test_account_data_without_values(self, mock_image, mock_profile):
        account = self._create_account()
        account._update_account_data()
        self.assertEqual(account.name, "Instagram Test")

    @patch(f"{ACCOUNT}._get_instagram_profile")
    @patch(f"{ACCOUNT}._instagram_profile_image", return_value=PNG_1X1)
    def test_account_data_refreshed(self, mock_image, mock_profile):
        account = self._create_account()
        mock_profile.return_value = {
            "username": "refreshed",
            "followers_count": 9,
            "profile_picture_url": "https://cdn/picture",
        }
        account._update_account_data()
        self.assertEqual(account.name, "refreshed")
        self.assertEqual(account.follower_count, 9)
        self.assertTrue(account.image_1920)

    def test_post_without_media(self):
        account = self._create_account()
        line = self._create_line(account)
        with self.assertRaisesRegex(UserError, "at least one image"):
            account._post_instagram_media(line)

    @patch(f"{REQUESTS}.post")
    @patch(f"{REQUESTS}.get")
    @patch(f"{REQUESTS}.Session")
    def test_post_with_a_carousel(self, mock_session, mock_get, mock_post):
        account = self._create_account()
        images = self._attachment("one.jpg") | self._attachment("two.jpg")
        post = self._create_post(account, images=images)
        line = self._create_line(account, post=post)
        session = MagicMock()
        session.post.side_effect = [
            self._response({"id": "container-1"}),
            self._response({"id": "container-2"}),
            self._response({"id": "carousel"}),
        ]
        mock_session.return_value = session
        mock_get.return_value = self._response({"status_code": "FINISHED"})
        mock_post.return_value = self._response({"id": "published"})
        self.assertEqual(account._post_instagram_media(line), "published")
        self.assertEqual(session.post.call_count, 3)

    @patch(f"{REQUESTS}.Session")
    def test_post_without_a_media_container(self, mock_session):
        account = self._create_account()
        post = self._create_post(account, images=self._attachment())
        line = self._create_line(account, post=post)
        session = MagicMock()
        session.post.return_value = self._response({})
        mock_session.return_value = session
        with self.assertRaisesRegex(UserError, "container of the media"):
            account._post_instagram_media(line)

    @patch(f"{REQUESTS}.Session")
    def test_post_without_a_carousel_container(self, mock_session):
        account = self._create_account()
        images = self._attachment("one.jpg") | self._attachment("two.jpg")
        post = self._create_post(account, images=images)
        line = self._create_line(account, post=post)
        session = MagicMock()
        session.post.side_effect = [
            self._response({"id": "container-1"}),
            self._response({"id": "container-2"}),
            self._response({}),
        ]
        mock_session.return_value = session
        with self.assertRaisesRegex(UserError, "carousel container"):
            account._post_instagram_media(line)

    @patch(f"{REQUESTS}.Session")
    def test_post_refused(self, mock_session):
        account = self._create_account()
        post = self._create_post(account, images=self._attachment())
        line = self._create_line(account, post=post)
        session = MagicMock()
        session.post.return_value = self._response(None, 500, text="refused")
        mock_session.return_value = session
        with self.assertRaisesRegex(UserError, "refused"):
            account._post_instagram_media(line)

    @patch(f"{REQUESTS}.post")
    def test_reel(self, mock_post):
        account = self._create_account()
        video = self._attachment("clip.mp4", data=b"video", mimetype="video/mp4")
        post = self._create_post(account, videos=video)
        line = self._create_line(account, post=post)
        with (
            patch.object(
                type(account), "_wait_instagram_container", return_value="container"
            ),
            patch.object(
                type(account), "_publish_instagram_container", return_value="published"
            ),
        ):
            mock_post.return_value = self._response({"id": "reel-container"})
            self.assertEqual(account._post_instagram_media(line), "published")

    @patch(f"{REQUESTS}.post")
    def test_reel_without_a_container(self, mock_post):
        account = self._create_account()
        video = self._attachment("clip.mp4", data=b"video", mimetype="video/mp4")
        post = self._create_post(account, videos=video)
        line = self._create_line(account, post=post)
        mock_post.return_value = self._response({})
        with self.assertRaisesRegex(UserError, "container of the reel"):
            account._post_instagram_media(line)

    @patch(f"{REQUESTS}.post")
    def test_reel_refused(self, mock_post):
        account = self._create_account()
        video = self._attachment("clip.mp4", data=b"video", mimetype="video/mp4")
        post = self._create_post(account, videos=video)
        line = self._create_line(account, post=post)
        mock_post.return_value = self._response(None, 500, text="no reel")
        with self.assertRaisesRegex(UserError, "no reel"):
            account._post_instagram_media(line)

    @patch(f"{REQUESTS}.get")
    def test_wait_container_finished(self, mock_get):
        account = self._create_account()
        mock_get.return_value = self._response({"status_code": "FINISHED"})
        self.assertEqual(account._wait_instagram_container("container"), "container")

    @patch(f"{REQUESTS}.get")
    def test_wait_container_in_error(self, mock_get):
        account = self._create_account()
        mock_get.return_value = self._response({"status_code": "ERROR"})
        with self.assertRaisesRegex(UserError, "failed to process"):
            account._wait_instagram_container("container")

    @patch(f"{REQUESTS}.get")
    def test_wait_container_refused(self, mock_get):
        account = self._create_account()
        mock_get.return_value = self._response(None, 500, text="no status")
        with self.assertRaisesRegex(UserError, "no status"):
            account._wait_instagram_container("container")

    @patch(f"{REQUESTS}.get")
    def test_wait_container_times_out(self, mock_get):
        account = self._create_account()
        mock_get.return_value = self._response({"status_code": "IN_PROGRESS"})
        with (
            patch(
                "odoo.addons.social_media_instagram.models.social_account.time.sleep"
            ),
            self.assertRaisesRegex(UserError, "timed out"),
        ):
            account._wait_instagram_container("container")

    @patch(f"{REQUESTS}.post")
    def test_publish_container(self, mock_post):
        account = self._create_account()
        mock_post.return_value = self._response({"id": "published"})
        self.assertEqual(account._publish_instagram_container("container"), "published")

    @patch(f"{REQUESTS}.post")
    def test_publish_container_refused(self, mock_post):
        account = self._create_account()
        mock_post.return_value = self._response(None, 500, text="no publish")
        with self.assertRaisesRegex(UserError, "no publish"):
            account._publish_instagram_container("container")

    def test_delete_media_without_a_reference(self):
        account = self._create_account()
        line = self._create_line(account)
        self.assertEqual(
            account._delete_instagram_media(line), {"success": True, "message": ""}
        )

    def test_delete_media_is_not_allowed(self):
        account = self._create_account()
        line = self._create_line(account, remote_ref="media-id")
        with self.assertRaisesRegex(UserError, "does not allow deleting"):
            account._delete_instagram_media(line)

    @patch(f"{REQUESTS}.get")
    def test_statistics_leave_other_medias_alone(self, mock_get):
        account = self._create_account()
        line = self._create_line(self.other_account)
        self.assertFalse(account._refresh_post_statistics(line))
        mock_get.assert_not_called()

    @patch(f"{REQUESTS}.get")
    def test_statistics_refused(self, mock_get):
        account = self._create_account()
        line = self._create_line(account, remote_ref="media-id")
        mock_get.return_value = self._response(None, 500, text="no stats")
        with self.assertRaisesRegex(UserError, "no stats"):
            account._refresh_post_statistics(line)
