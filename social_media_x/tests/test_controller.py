# Copyright 2026 Binhex <https://www.binhex.cloud>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from odoo.tests.common import HttpCase, tagged

from odoo.addons.social_media_base.tests.test_social_common import (
    PATCH_SOCIAL_BASE_MIXIN,
)
from odoo.addons.social_media_x.tests.test_common_x import PATCH_ACCOUNT_X

PATCH_SOCIAL_ACCOUNT = PATCH_ACCOUNT_X.format("SocialAccount.{}")


@tagged("post_install", "-at_install")
class TestSociaXlController(HttpCase):
    def setUp(self):
        super().setUp()
        # The messages are asserted in their source language, so the user
        # answering the callback must not translate them.
        self.env["res.users"].search([("login", "=", "admin")]).lang = "en_US"
        self.authenticate("admin", "admin")

    def test_callback_creates_account_when_tokens_present(self):
        access_token = "tok"
        access_secret = "sec"
        with patch(
            PATCH_SOCIAL_ACCOUNT.format("_get_access_token"),
            autospec=True,
            return_value=(access_token, access_secret),
        ) as mocked_get_token, patch(
            PATCH_SOCIAL_ACCOUNT.format("create_account_x"),
            autospec=True,
        ) as mocked_create:
            resp = self.url_open("/social_x/callback?oauth_token=1&oauth_verifier=2")
            mocked_get_token.assert_called_once()
            mocked_create.assert_called_once()
            _, args, kwargs = mocked_create.mock_calls[0]
            self.assertEqual(args[1], access_token)
            self.assertEqual(args[2], access_secret)
            self.assertIsInstance(args[3], dict)
            self.assertEqual(resp.status_code, 200)
            self.assertIn("/web", resp.url)

    def test_callback_success_notifies_user(self):
        """The association answers a redirect, so it reports through the session."""
        fake_client = MagicMock()
        data = fake_client.get_me.return_value.data
        data.id = "24680"
        data.name = "Callback X"
        data.username = "callback-x-user"
        data.profile_image_url = "https://example.com/img_url"
        wizard = SimpleNamespace(x_api_key="KEY", x_api_secret="SECRET")
        SocialAccount = type(self.env["social.account"])
        with patch(
            PATCH_SOCIAL_ACCOUNT.format("_get_access_token"),
            autospec=True,
            return_value=("tok", "sec"),
        ), patch.object(
            SocialAccount, "get_client_api", autospec=True, return_value=fake_client
        ), patch.object(
            SocialAccount, "_get_x_oauth_wizard", autospec=True, return_value=wizard
        ), patch.object(
            SocialAccount,
            "_get_access_token_oauth2",
            autospec=True,
            return_value="oauth2-token",
        ), patch.object(
            SocialAccount,
            "_x_download_profile_image",
            autospec=True,
            return_value=False,
        ), patch.object(
            SocialAccount, "_x_refresh_credit_balance", autospec=True
        ), patch.object(SocialAccount, "_on_account_associated", autospec=True), patch(
            PATCH_SOCIAL_BASE_MIXIN.format("_notify_user_session"),
            autospec=True,
        ) as mocked_notify:
            resp = self.url_open("/social_x/callback?oauth_token=1&oauth_verifier=2")

        mocked_notify.assert_called_once()
        _, args, kwargs = mocked_notify.mock_calls[0]
        self.assertIn("associated successfully", args[1])
        self.assertNotIn("ERROR:", args[1])
        self.assertEqual(kwargs["message_type"], "success")
        self.assertEqual(resp.status_code, 200)

    def test_callback_does_not_create_account_when_tokens_missing(self):
        with patch(
            PATCH_SOCIAL_ACCOUNT.format("_get_access_token"),
            autospec=True,
            return_value=(None, None),
        ) as mocked_get_token, patch(
            PATCH_SOCIAL_ACCOUNT.format("create_account_x"),
            autospec=True,
        ) as mocked_create:
            resp = self.url_open("/social_x/callback?oauth_token=1&oauth_verifier=2")
            mocked_get_token.assert_called_once()
            mocked_create.assert_not_called()
            self.assertEqual(resp.status_code, 200)
            self.assertIn("/web", resp.url)

    def test_callback_logs_error_on_exception_and_redirects(self):
        with patch(
            PATCH_SOCIAL_ACCOUNT.format("_get_access_token"),
            autospec=True,
            side_effect=Exception("exception_error"),
        ), patch(
            PATCH_SOCIAL_BASE_MIXIN.format("_notify_user_session"),
            autospec=True,
        ) as mocked_notify, patch(
            "odoo.addons.social_media_x.controllers.social_media_x._logger",
            autospec=True,
        ) as mocked_logger:
            resp = self.url_open("/social_x/callback?oauth_token=1&oauth_verifier=2")
            mocked_notify.assert_called_once()
            _, args, _kwargs = mocked_notify.mock_calls[0]
            self.assertIn("Social Media X", args[1])
            self.assertIn("could not be associated", args[1])
            # The provider detail must never reach the user.
            self.assertNotIn("exception_error", args[1])
            mocked_logger.exception.assert_called_once()
            self.assertEqual(resp.status_code, 200)
            self.assertIn("/web", resp.url)
