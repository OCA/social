# Copyright 2025 Binhex <https://www.binhex.cloud>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).


from odoo.addons.social_media_x.tests.test_common_x import (
    TestSocialCommonX,
)

from ..social_x_utils import _get_code_challenge, _get_oauth


class TestSocialMediaX(TestSocialCommonX):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

    def test_get_account_by_media(self):
        result = self.media_x_id._get_account_by_media()
        self.assertEqual(result, 2)

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

    def test_open_action_account_media_x(self):
        action = self.media_x_id.open_action_account()
        self.assertIsInstance(action, dict)
        self.assertEqual(action.get("type"), "ir.actions.act_window")
        self.assertEqual(action.get("res_model"), self.WizardAccount._name)
        self.assertEqual(action.get("target"), "new")
        ctx = action.get("context") or {}
        self.assertEqual(ctx.get("default_media_id"), self.media_x_id.id)
