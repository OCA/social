# Copyright 2025 Binhex <https://www.binhex.cloud>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from unittest.mock import patch

from odoo.addons.social_media_base.tests.test_social_common import (
    PATCH_MEDIA,
)
from odoo.addons.social_media_x.tests.test_common_x import (
    TestSocialCommonX,
)

from ..social_x_utils import _get_code_challenge, _get_oauth


class TestSocialMediaX(TestSocialCommonX):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

    def test_get_oauth(self):
        request_access_token = {
            "oauth_token": "TEST-ACCESS-TOKEN",
            "oauth_token_secret": "TEST-ACCESS-TOKEN-SECRET",
        }
        result = _get_oauth(
            api_key="TEST-API-KEY",
            api_secret="TEST-API-SECRET",
            request_access_token=request_access_token,
        )
        self.assertEqual(result.client.client_key, "TEST-API-KEY")
        self.assertEqual(result.client.client_secret, "TEST-API-SECRET")
        self.assertEqual(result.client.resource_owner_key, "TEST-ACCESS-TOKEN")
        self.assertEqual(
            result.client.resource_owner_secret, "TEST-ACCESS-TOKEN-SECRET"
        )
        result = _get_oauth(
            api_key="TEST-API-KEY",
            api_secret="TEST-API-SECRET",
            request_access_token=None,
        )
        self.assertEqual(result.client.client_key, "TEST-API-KEY")
        self.assertEqual(result.client.client_secret, "TEST-API-SECRET")
        self.assertEqual(result.client.resource_owner_key, None)
        self.assertEqual(result.client.resource_owner_secret, None)

    def test_get_code_challenge(self):
        code_challenge = _get_code_challenge()
        self.assertIsInstance(code_challenge, str)
        self.assertTrue(len(code_challenge) > 0)
        self.assertRegex(code_challenge, r"^[A-Za-z0-9_-]+$")
        self.assertGreaterEqual(len(code_challenge), 43)
        self.assertLessEqual(len(code_challenge), 128)

    def test_open_action_account(self):
        with patch(
            PATCH_MEDIA.format("open_action_account")
        ) as mock_open_action_account:
            res = self.media_x_id.open_action_account()
            self.assertEqual(res["context"]["default_media_id"], self.media_x_id.id)
            mock_open_action_account.assert_called_once()

        with patch(
            PATCH_MEDIA.format("open_action_account")
        ) as mock__open_action_account:
            self.SocialMedia.open_action_account()
            mock__open_action_account.assert_called_once()