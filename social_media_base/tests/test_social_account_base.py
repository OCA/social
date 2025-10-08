# Copyright 2025 Binhex <https://www.binhex.cloud>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from unittest.mock import patch

from odoo.addons.social_media_base.tests.test_social_common import (
    TestSocialMediaBaseCommon,
)

from .test_social_common import (
    PATCH_ACCOUNT,
)


class TestSocialAccountBase(TestSocialMediaBaseCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

    def test_get_account_by_media(self):
        result = self.SocialMediaBaseMixin._get_account_by_media()
        self.assertEqual(result, None)

    def test_action_pass(self):
        result = self.SocialPostAccount._action_post()
        self.assertIsNone(result)

        result = self.SocialPostAccount._action_campaign_post(None)
        self.assertIsNone(result)

        result = self.SocialPostAccount.delete_post_account()
        self.assertEqual(
            "The post was successfully deleted.", result["params"]["message"]
        )

        result = self.social_account_id.validate_access_token()
        self.assertIsNone(result)

        result = self.social_account_id._load_ads_accounts()
        self.assertIsInstance(result, dict)

        result = self.social_account_id.load_ads_accounts()
        self.assertIsInstance(result, dict)

    def test_compute_display_name(self):
        self.social_account_id._compute_display_name()
        self.assertEqual(self.social_account_id.display_name, "Linkedin")

    @patch(PATCH_ACCOUNT.format("_get_chart_account_statistics"))
    def test_get_chart_account_statistics(self, mock_get_chart_account_statistics):
        self.social_account_id.get_chart_account_statistics()
        mock_get_chart_account_statistics.assert_called_once()
