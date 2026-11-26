# Copyright 2026 Domatix <https://www.domatix.cloud>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from unittest.mock import patch

from odoo.exceptions import AccessError, UserError
from odoo.tools import mute_logger

from odoo.addons.social_media_base.exceptions import SocialCredentialsError

from .. import uninstall_hook
from .common import FacebookCommon

REQUESTS = "odoo.addons.social_media_facebook.models.social_account.requests"
LOGGER = "odoo.addons.social_media_facebook.models.social_account"


class TestSocialAccountFacebook(FacebookCommon):
    """The Facebook calls of ``social.account``."""

    def test_uninstall_hook_clears_the_credentials(self):
        account = self._create_account()
        uninstall_hook(self.env)
        self.assertFalse(account.active)
        for field in (
            "facebook_access_token",
            "facebook_account_id",
            "facebook_app_id",
            "facebook_app_secret",
        ):
            self.assertFalse(account[field])

    def test_facebook_redirect_uri(self):
        account = self._create_account()
        self.assertTrue(
            account._facebook_redirect_uri().endswith("/social_facebook/callback")
        )

    def test_check_error_accepts_a_success(self):
        account = self._create_account()
        account._facebook_check_error(self._response({}), "Anything")

    def test_check_error_means_dead_credentials(self):
        account = self._create_account()
        response = self._response({"error": {"code": 190}}, status_code=400)
        with self.assertRaises(SocialCredentialsError):
            account._facebook_check_error(response, "Anything")

    def test_check_error_without_json_is_a_plain_error(self):
        account = self._create_account()
        response = self._response(None, status_code=500, text="boom")
        with self.assertRaisesRegex(UserError, "boom"):
            account._facebook_check_error(response, "Anything")

    def test_check_error_with_another_code_is_a_plain_error(self):
        account = self._create_account()
        response = self._response({"error": {"code": 100}}, status_code=403)
        with self.assertRaises(UserError):
            account._facebook_check_error(response, "Anything")

    def test_get_removal_values(self):
        values = self._create_account()._get_removal_values()
        self.assertFalse(values["facebook_access_token"])
        self.assertFalse(values["facebook_account_id"])
        self.assertFalse(values["facebook_app_id"])
        self.assertFalse(values["facebook_app_secret"])

    def test_oauth_wizard_without_state(self):
        account = self._create_account()
        self.assertFalse(account._get_facebook_oauth_wizard(False))

    def test_oauth_wizard_matches_the_state_and_the_user(self):
        account = self._create_account()
        wizard = self._create_wizard(csrf_state_token="state-token")
        self.assertEqual(account._get_facebook_oauth_wizard("state-token"), wizard)

    def test_consume_oauth_wizard_deletes_it(self):
        account = self._create_account()
        wizard = self._create_wizard(csrf_state_token="state-token")
        account._consume_facebook_oauth_wizard("state-token")
        self.assertFalse(wizard.exists())

    @patch(f"{REQUESTS}.post")
    def test_access_token_refused_by_facebook(self, mock_post):
        wizard = self._create_wizard(
            facebook_app_id="app-id",
            facebook_app_secret="app-secret",
            csrf_state_token="state-token",
        )
        self.assertTrue(wizard)
        mock_post.return_value = self._response(None, 500, text="no token")
        with self.assertRaisesRegex(UserError, "no token"):
            self.env["social.account"].get_access_token_facebook("code", "state-token")

    @patch(f"{REQUESTS}.get")
    @patch(f"{REQUESTS}.post")
    def test_long_lived_token_refused(self, mock_post, mock_get):
        self._create_wizard(
            facebook_app_id="app-id",
            facebook_app_secret="app-secret",
            csrf_state_token="state-token",
        )
        mock_post.return_value = self._response({"access_token": "short"})
        mock_get.return_value = self._response(None, 500, text="no exchange")
        with self.assertRaisesRegex(UserError, "no exchange"):
            self.env["social.account"].get_access_token_facebook("code", "state-token")

    @patch(f"{REQUESTS}.get")
    @patch(f"{REQUESTS}.post")
    def test_long_lived_token_falls_back_to_the_short_one(self, mock_post, mock_get):
        self._create_wizard(
            facebook_app_id="app-id",
            facebook_app_secret="app-secret",
            csrf_state_token="state-token",
        )
        mock_post.return_value = self._response({"access_token": "short"})
        mock_get.return_value = self._response({})
        _, _, token = self.env["social.account"].get_access_token_facebook(
            "code", "state-token"
        )
        self.assertEqual(token, "short")

    @patch(f"{REQUESTS}.get")
    def test_pages_follow_pagination(self, mock_get):
        account = self._create_account()
        mock_get.side_effect = [
            self._response({"data": [{"id": "1"}], "paging": {"next": "https://next"}}),
            self._response({"data": [{"id": "2"}]}),
        ]
        pages = account._get_facebook_pages("token")
        self.assertEqual([page["id"] for page in pages], ["1", "2"])
        self.assertEqual(mock_get.call_count, 2)

    @patch(f"{REQUESTS}.get")
    def test_pages_refused(self, mock_get):
        account = self._create_account()
        mock_get.return_value = self._response(None, 500, text="no pages")
        with self.assertRaisesRegex(UserError, "no pages"):
            account._get_facebook_pages("token")

    @patch(
        "odoo.addons.social_media_facebook.models.social_account."
        "SocialAccount._get_facebook_pages"
    )
    def test_create_accounts_one_per_page(self, mock_pages):
        mock_pages.return_value = [
            {"id": "page-1", "name": "Page one", "access_token": "token-1"},
            {"id": "page-2", "name": "Page two", "access_token": "token-2"},
        ]
        self.env["social.account"].create_facebook_accounts(
            "app-id", "app-secret", "user-token"
        )
        accounts = self.env["social.account"].search([("media_type", "=", "facebook")])
        self.assertEqual(len(accounts), 2)
        self.assertEqual(accounts.mapped("remote_ref"), ["page-1", "page-2"])
        self.assertEqual(
            accounts.mapped("facebook_access_token"), ["token-1", "token-2"]
        )
        self.assertEqual(accounts.mapped("facebook_app_secret"), ["app-secret"] * 2)

    @patch(
        "odoo.addons.social_media_facebook.models.social_account."
        "SocialAccount._get_facebook_pages"
    )
    def test_create_accounts_without_pages(self, mock_pages):
        mock_pages.return_value = []
        with self.assertRaisesRegex(UserError, "Could not find any Facebook page"):
            self.env["social.account"].create_facebook_accounts(
                "app", "secret", "token"
            )

    @patch(
        "odoo.addons.social_media_facebook.models.social_account."
        "SocialAccount._get_facebook_pages"
    )
    def test_create_accounts_with_incomplete_pages(self, mock_pages):
        mock_pages.return_value = [{"id": False, "access_token": False}]
        with self.assertRaisesRegex(UserError, "at least one Facebook page"):
            self.env["social.account"].create_facebook_accounts(
                "app", "secret", "token"
            )

    @patch(
        "odoo.addons.social_media_facebook.models.social_account."
        "SocialAccount._get_facebook_pages"
    )
    def test_create_accounts_reactivates_an_archived_one(self, mock_pages):
        existing = self._create_account(
            remote_ref="page-1", facebook_account_id="page-1", active=False
        )
        mock_pages.return_value = [
            {"id": "page-1", "name": "Page one", "access_token": "new-token"}
        ]
        self.env["social.account"].create_facebook_accounts("app", "secret", "token")
        existing.invalidate_recordset()
        self.assertTrue(existing.active)
        self.assertEqual(existing.name, "Page one")
        self.assertEqual(existing.facebook_access_token, "new-token")

    @patch(
        "odoo.addons.social_media_facebook.models.social_account."
        "SocialAccount._get_facebook_pages"
    )
    def test_create_accounts_updates_an_active_one(self, mock_pages):
        existing = self._create_account(remote_ref="page-1")
        mock_pages.return_value = [
            {"id": "page-1", "name": "Renamed", "access_token": "new-token"}
        ]
        self.env["social.account"].create_facebook_accounts("app", "secret", "token")
        existing.invalidate_recordset()
        self.assertTrue(existing.active)
        self.assertEqual(existing.name, "Renamed")

    def test_open_account_of_another_media(self):
        self.assertIsNone(self.other_media.action_open_account())

    @patch(
        "odoo.addons.social_media_facebook.models.social_account."
        "SocialAccount._get_facebook_pages"
    )
    def test_create_accounts_refuses_another_users_page(self, mock_pages):
        existing = self._create_account(remote_ref="page-1")
        self.assertTrue(existing)
        mock_pages.return_value = [
            {"id": "page-1", "name": "Page one", "access_token": "token-1"}
        ]
        user = self._create_social_user("facebook_other_user")
        with self.assertRaises(AccessError):
            self.env["social.account"].with_user(user).create_facebook_accounts(
                "app", "secret", "token"
            )

    @patch(f"{REQUESTS}.get")
    def test_account_data_refreshed(self, mock_get):
        account = self._create_account()
        mock_get.return_value = self._response(
            {"name": "Page", "username": "page", "followers_count": 12}
        )
        account._update_account_data()
        self.assertEqual(account.name, "Page")
        self.assertEqual(account.username, "page")
        self.assertEqual(account.follower_count, 12)

    @patch(f"{REQUESTS}.get")
    def test_account_data_falls_back_to_the_fans(self, mock_get):
        account = self._create_account()
        mock_get.return_value = self._response({"name": "Page", "fan_count": 7})
        account._update_account_data()
        self.assertEqual(account.follower_count, 7)

    @patch(f"{REQUESTS}.get")
    def test_account_data_without_figures(self, mock_get):
        account = self._create_account()
        mock_get.return_value = self._response({"name": "Page"})
        account._update_account_data()
        self.assertEqual(account.follower_count, 0)

    @mute_logger(LOGGER)
    @patch(f"{REQUESTS}.get")
    def test_account_data_refused_keeps_the_account(self, mock_get):
        account = self._create_account()
        mock_get.return_value = self._response(None, 500, text="no data")
        account._update_account_data()
        self.assertEqual(account.name, "Facebook Test")
        self.assertEqual(account.follower_count, 0)

    def test_account_data_of_another_media(self):
        self.assertFalse(self.other_account._update_account_data())

    @patch(f"{REQUESTS}.get")
    def test_validate_token_against_facebook(self, mock_get):
        account = self._create_account()
        mock_get.return_value = self._response({"id": "page-id"})
        self.assertFalse(account.action_validate_access_token())
        mock_get.assert_called_once()

    @patch(f"{REQUESTS}.get")
    def test_validate_token_refused(self, mock_get):
        account = self._create_account()
        mock_get.return_value = self._response(
            {"error": {"code": 190}}, status_code=400
        )
        with self.assertRaises(SocialCredentialsError):
            account.action_validate_access_token()

    @patch(f"{REQUESTS}.get")
    def test_validate_token_is_local_without_the_flag(self, mock_get):
        account = self._create_account()
        self.assertFalse(account.validate_access_token())
        mock_get.assert_not_called()

    def test_validate_token_of_another_media(self):
        self.assertFalse(self.other_account.action_validate_access_token())

    def test_refresh_credentials_needs_the_user(self):
        self.assertFalse(self._create_account()._refresh_credentials())

    def test_refresh_credentials_of_another_media(self):
        self.assertFalse(self.other_account._refresh_credentials())

    @patch(f"{REQUESTS}.post")
    def test_post_with_one_image(self, mock_post):
        account = self._create_account()
        image = self._attachment("photo.png")
        post = self._create_post(account, images=image)
        line = self._create_line(account, post=post)
        mock_post.return_value = self._response({"id": "photo-post"})
        result = account._post_facebook(line)
        self.assertEqual(result, "photo-post")
        self.assertIn("/photos", mock_post.call_args.args[0])

    @patch(f"{REQUESTS}.post")
    def test_post_with_several_images(self, mock_post):
        account = self._create_account()
        images = self._attachment("one.png") | self._attachment("two.png")
        post = self._create_post(account, images=images)
        line = self._create_line(account, post=post)
        mock_post.side_effect = [
            self._response({"id": "photo-1"}),
            self._response({}),
            self._response({"post_id": "album-post"}),
        ]
        result = account._post_facebook(line)
        self.assertEqual(result, "album-post")
        self.assertEqual(mock_post.call_count, 3)
        self.assertIn("/feed", mock_post.call_args.args[0])

    @patch(f"{REQUESTS}.post")
    def test_album_refused(self, mock_post):
        account = self._create_account()
        images = self._attachment("one.png") | self._attachment("two.png")
        post = self._create_post(account, images=images)
        line = self._create_line(account, post=post)
        mock_post.return_value = self._response(None, 500, text="no album")
        with self.assertRaisesRegex(UserError, "no album"):
            account._post_facebook(line)

    @patch(f"{REQUESTS}.post")
    def test_post_with_video(self, mock_post):
        account = self._create_account()
        video = self._attachment("clip.mp4", data=b"video")
        post = self._create_post(account, videos=video)
        line = self._create_line(account, post=post)
        mock_post.return_value = self._response({"id": "video-post"})
        result = account._post_facebook(line)
        self.assertEqual(result, "video-post")
        self.assertIn("/videos", mock_post.call_args.args[0])

    @patch(f"{REQUESTS}.post")
    def test_video_refused(self, mock_post):
        account = self._create_account()
        video = self._attachment("clip.mp4", data=b"video")
        post = self._create_post(account, videos=video)
        line = self._create_line(account, post=post)
        mock_post.return_value = self._response(None, 500, text="no video")
        with self.assertRaisesRegex(UserError, "no video"):
            account._post_facebook(line)

    @patch(f"{REQUESTS}.post")
    def test_post_falls_back_to_the_id(self, mock_post):
        account = self._create_account()
        post = self._create_post(account)
        line = self._create_line(account, post=post)
        mock_post.return_value = self._response({"id": "only-id"})
        self.assertEqual(account._post_facebook(line), "only-id")

    def test_delete_post_without_reference(self):
        account = self._create_account()
        line = self._create_line(account)
        self.assertEqual(
            account._delete_facebook_post(line), {"success": True, "message": ""}
        )

    @patch(f"{REQUESTS}.delete")
    def test_delete_post(self, mock_delete):
        account = self._create_account()
        line = self._create_line(account, remote_ref="post-id")
        mock_delete.return_value = self._response({})
        self.assertTrue(account._delete_facebook_post(line)["success"])

    @patch(f"{REQUESTS}.delete")
    def test_delete_post_refused(self, mock_delete):
        account = self._create_account()
        line = self._create_line(account, remote_ref="post-id")
        mock_delete.return_value = self._response(None, 500, text="no delete")
        with self.assertRaisesRegex(UserError, "no delete"):
            account._delete_facebook_post(line)

    @patch(f"{REQUESTS}.get")
    def test_statistics_leave_other_medias_alone(self, mock_get):
        account = self._create_account()
        line = self._create_line(self.other_account)
        refreshed = account._refresh_post_statistics(line)
        self.assertFalse(refreshed)
        mock_get.assert_not_called()

    @patch(f"{REQUESTS}.get")
    def test_statistics_of_a_mixed_batch(self, mock_get):
        account = self._create_account()
        facebook_line = self._create_line(account, remote_ref="post-id")
        other_line = self._create_line(self.other_account)
        mock_get.return_value = self._response(
            {"likes": {"summary": {"total_count": 3}}}
        )
        refreshed = account._refresh_post_statistics(facebook_line | other_line)
        self.assertEqual(refreshed, facebook_line)
        self.assertEqual(facebook_line.like_count, 3)
        self.assertFalse(other_line.like_count)

    @patch(f"{REQUESTS}.get")
    def test_statistics_refused(self, mock_get):
        account = self._create_account()
        line = self._create_line(account, remote_ref="post-id")
        mock_get.return_value = self._response(None, 500, text="no stats")
        with self.assertRaisesRegex(UserError, "no stats"):
            account._refresh_post_statistics(line)
