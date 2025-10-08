# Copyright 2025 Binhex <https://www.binhex.cloud>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from unittest.mock import patch

from odoo.addons.social_media_linkedin.tests.test_common_linkedin import (
    TestSocialCommonLinkedin,
)

PATCH_UTILS = "odoo.addons.social_media_linkedin.social_linkedin_utils.{}"
PATCH_BASE_LINKEDIN = "odoo.addons.social_media_linkedin.models.{}"
PATCH_LINKEDIN_MEDIA = PATCH_BASE_LINKEDIN.format("social_media.SocialMedia.{}")


class TestSocialNetworkLinkedin(TestSocialCommonLinkedin):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

    @patch(
        PATCH_UTILS.format("_HEADERS_LINKEDIN"),
        {
            "X-Restli-Protocol-Version": "2.0.0",
            "LinkedIn-Version": "202411",
        },
    )
    def test_get_linkedin_headers_with_token_and_content_type(self):
        access_token = "fake-token"
        content_type = "application/json"
        headers = self.SocialMedia._get_linkedin_headers(access_token, content_type)

        self.assertIn("Authorization", headers)
        self.assertEqual(headers["Authorization"], f"Bearer {access_token}")
        self.assertIn("Content-Type", headers)
        self.assertEqual(headers["Content-Type"], content_type)
        self.assertIn("LinkedIn-Version", headers)
        self.assertIn("X-Restli-Protocol-Version", headers)

    def test_get_account_by_media(self):
        result = self.media_linkedin_id._get_account_by_media()
        self.assertEqual(result, 1)
