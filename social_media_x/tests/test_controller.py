# Copyright 2025 Binhex <https://www.binhex.cloud>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from unittest.mock import patch

from odoo.tests.common import HttpCase, tagged

from odoo.addons.social_media_x.tests.test_common_x import PATCH_ACCOUNT_X

PATCH_SOCIAL_ACCOUNT = PATCH_ACCOUNT_X.format("SocialAccount.{}")


@tagged("post_install", "-at_install")
class TestSociaXlController(HttpCase):
    def setUp(self):
        super().setUp()
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
            "odoo.addons.social_media_x.controllers.social_media_x._logger",
            autospec=True,
        ) as mocked_logger:
            resp = self.url_open("/social_x/callback?oauth_token=1&oauth_verifier=2")
            mocked_logger.error.assert_called_once()
            self.assertEqual(resp.status_code, 200)
            self.assertIn("/web", resp.url)
