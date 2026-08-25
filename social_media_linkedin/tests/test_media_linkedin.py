# Copyright 2026 Binhex <https://www.binhex.cloud>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).


from odoo.addons.social_media_linkedin.tests.test_common_linkedin import (
    TestSocialCommonLinkedin,
)

from ..social_linkedin_utils import _HEADERS_LINKEDIN


class TestSocialMediaLinkedin(TestSocialCommonLinkedin):
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

    def test_action_open_account_media_linkedin(self):
        action = self.media_linkedin_id.action_open_account()
        self.valid_action_open_account_media(self.media_linkedin_id, action)

    def test_not_action_open_account_media_linkedin(self):
        self.valid_not_action_open_account_media()

    def test_linkedin_media_reports_the_linkedin_medium(self):
        self.assertEqual(
            self.media_linkedin_id._get_utm_medium(),
            self.env.ref("utm.utm_medium_linkedin"),
        )

    def test_a_configured_medium_wins_over_the_linkedin_one(self):
        medium = self.env["utm.medium"].create({"name": "Configured medium"})
        self.media_linkedin_id.utm_medium_id = medium
        self.assertEqual(self.media_linkedin_id._get_utm_medium(), medium)
