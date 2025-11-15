# Copyright 2025 Binhex <https://www.binhex.cloud>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from unittest.mock import patch

from odoo.tests.common import HttpCase, tagged

from odoo.addons.social_media_base.tests.test_social_common import (
    PATCH_SOCIAL_BASE_MIXIN,
)
from odoo.addons.social_media_linkedin.controllers.social_media_linkedin import (
    SocialMediaLinkedin,
)
from odoo.addons.social_media_linkedin.tests.test_common_linkedin import (
    PATCH_ACCOUNT_LINKEDIN,
    TestSocialCommonLinkedin,
)


@tagged("post_install", "-at_install")
class TestSocialController(HttpCase, TestSocialCommonLinkedin):
    def setUp(cls):
        super().setUp()
        cls.controller = SocialMediaLinkedin()
        cls.authenticate("admin", "admin")

    def test_social_linkedin_webhook(self):
        controller = SocialMediaLinkedin()
        result = controller.social_linkedin_webhook()
        self.assertTrue(result)

    def test_callback_with_access_token_skips_exchange_and_creates_account(self):
        token = "ACCESS_TOKEN"
        with patch(
            PATCH_ACCOUNT_LINKEDIN.format("get_access_token_linkedin"),
            autospec=True,
        ) as mocked_exchange, patch(
            PATCH_ACCOUNT_LINKEDIN.format("create_account_linkedin"),
            autospec=True,
        ) as mocked_create:
            resp = self.url_open(f"/linkedin/callback?access_token={token}")
            mocked_exchange.assert_not_called()
            mocked_create.assert_called_once()
            _, args, _kwargs = mocked_create.mock_calls[0]
            self.assertIsNone(args[1])
            self.assertIsNone(args[2])
            self.assertEqual(args[3], token)
            self.assertEqual(resp.status_code, 200)
            self.assertIn("/web", resp.url)

    def test_callback_without_access_token_exchanges_code_and_creates_account(self):
        code = "AUTH_CODE"
        client_id = "CID"
        client_secret = "CSEC"
        token = "NEW_TOKEN"
        with patch(
            PATCH_ACCOUNT_LINKEDIN.format("get_access_token_linkedin"),
            autospec=True,
            return_value=(client_id, client_secret, token),
        ) as mocked_exchange, patch(
            PATCH_ACCOUNT_LINKEDIN.format("create_account_linkedin"),
            autospec=True,
        ) as mocked_create:
            resp = self.url_open(f"/linkedin/callback?code={code}")
            mocked_exchange.assert_called_once()
            mocked_create.assert_called_once()
            _, args, _kwargs = mocked_create.mock_calls[0]
            self.assertEqual(args[1], client_id)
            self.assertEqual(args[2], client_secret)
            self.assertEqual(args[3], token)
            self.assertEqual(resp.status_code, 200)
            self.assertIn("/web", resp.url)

    def test_callback_exception_notifies_user_and_redirects(self):
        with patch(
            PATCH_ACCOUNT_LINKEDIN.format("get_access_token_linkedin"),
            autospec=True,
            side_effect=Exception("boom"),
        ), patch(
            PATCH_SOCIAL_BASE_MIXIN.format("_notify_user_client"),
            autospec=True,
        ) as mocked_notify, patch(
            "odoo.addons.social_media_linkedin.controllers.social_media_linkedin._logger",
            autospec=True,
        ) as mocked_logger:
            resp = self.url_open("/linkedin/callback?code=ANY")

            mocked_notify.assert_called_once()
            _, _args, kwargs = mocked_notify.mock_calls[0]
            self.assertEqual(kwargs["notif_type"], "social_kanban_danger")
            self.assertEqual(kwargs["media"], "linkedin")
            self.assertIn("notif_message", kwargs)
            mocked_logger.error.assert_called_once()
            self.assertEqual(resp.status_code, 200)
            self.assertIn("/web", resp.url)