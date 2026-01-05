# Copyright 2025 Binhex <https://www.binhex.cloud>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).


from odoo.addons.social_media_linkedin.tests.test_common_linkedin import (
    TestSocialCommonLinkedin,
)

from ..social_linkedin_utils import _HEADERS_LINKEDIN

PATCH_UTILS = "odoo.addons.social_media_linkedin.social_linkedin_utils.{}"
PATCH_BASE_LINKEDIN = "odoo.addons.social_media_linkedin.models.{}"
PATCH_LINKEDIN_MEDIA = PATCH_BASE_LINKEDIN.format("social_media.SocialMedia.{}")


class TestSocialNetworkLinkedin(TestSocialCommonLinkedin):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

    def test_get_linkedin_headers(self):
        headers = self.media_linkedin_id._get_linkedin_headers()
        self.assertEqual(headers, _HEADERS_LINKEDIN)
        self.assertIsNot(headers, _HEADERS_LINKEDIN)
        headers = self.media_linkedin_id._get_linkedin_headers(x_restli_method="PATCH")
        self.assertEqual(headers["X-RestLi-Method"], "PATCH")
        for key, value in _HEADERS_LINKEDIN.items():
            self.assertEqual(headers[key], value)
        token = "test_access_token"
        headers = self.media_linkedin_id._get_linkedin_headers(access_token=token)
        self.assertEqual(headers["Authorization"], f"Bearer {token}")
        headers = self.media_linkedin_id._get_linkedin_headers(
            content_type="application/json"
        )
        self.assertEqual(headers["Content-Type"], "application/json")
        token = "test_access_token"
        headers = self.media_linkedin_id._get_linkedin_headers(
            access_token=token,
            content_type="application/json",
            x_restli_method="POST",
        )
        self.assertEqual(headers["Authorization"], f"Bearer {token}")
        self.assertEqual(headers["Content-Type"], "application/json")
        self.assertEqual(headers["X-RestLi-Method"], "POST")

        for key, value in _HEADERS_LINKEDIN.items():
            self.assertEqual(headers[key], value)
        self.media_linkedin_id._get_linkedin_headers(
            access_token="abc",
            content_type="application/json",
            x_restli_method="PUT",
        )
        self.assertEqual(_HEADERS_LINKEDIN, _HEADERS_LINKEDIN.copy())

    def test_open_action_account_media_linkedin(self):
        action = self.media_linkedin_id.open_action_account()
        self.valid_open_action_account_media(self.media_linkedin_id, action)

    def test_not_open_action_account_media_linkedin(self):
        self.valid_not_open_action_account_media()
