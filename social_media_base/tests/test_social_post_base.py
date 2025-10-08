# Copyright 2025 Binhex <https://www.binhex.cloud>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from datetime import datetime, timedelta
from unittest.mock import patch

from odoo.addons.social_media_base.tests.test_social_common import (
    TestSocialMediaBaseCommon,
)

from .test_social_common import (
    PATCH_POST,
    PATCH_POST_ACCOUNT,
)


class TestSocialPostBase(TestSocialMediaBaseCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

    def test_compute_send_post_date(self):
        self.social_post_id.send_post = "schedule"
        self.social_post_id._compute_send_post_date()
        self.assertEqual(
            self.social_post_id.send_post_date.strftime("%Y-%m-%d"),
            (datetime.now() + timedelta(hours=1)).strftime("%Y-%m-%d"),
        )
        self.assertEqual(self.social_post_id.state, "planned")

    def test_compute_post_statistics(self):
        self.social_post_id._compute_post_statistics()
        self.assertEqual(self.social_post_id.count_post_likes, 0)
        self.assertEqual(self.social_post_id.count_post_shares, 0)
        self.assertEqual(self.social_post_id.count_post_likes, 0)
        self.assertEqual(self.social_post_id.count_post_engagement, 0)
        self.assertEqual(self.social_post_id.count_post_impression, 0)
        self.assertEqual(self.social_post_id.count_post_comments, 0)
        self.assertEqual(self.social_post_id.count_post_interactions, 0)

    @patch(PATCH_POST.format("_action_create_post_account"))
    def test_run_send_post(self, mock_action_create_post_account):
        self.social_post_id._run_send_post()
        mock_action_create_post_account.assert_called_once()

    @patch(PATCH_POST.format("_action_create_post_account"))
    def test_action_create_post_account(self, mock_action_create_post_account):
        self.social_post_id.action_create_post_account()
        mock_action_create_post_account.assert_called_once()

    @patch(PATCH_POST_ACCOUNT.format("_action_post"))
    def test__action_create_post_account(self, mock_action_post):
        self.social_post_id._action_create_post_account()
        mock_action_post.assert_called_once()

    def test_compute_display_name(self):
        self.social_post_id._compute_display_name()
        self.assertEqual(self.social_post_id.display_name, "Post on Linkedin")

    def test_comments(self):
        result = self.social_post_account_id.create_comment({})
        self.assertIsNone(result)

        result = self.social_post_account_id.get_comments()
        self.assertIsInstance(result, dict)
        self.assertEqual(result, {"success": False, "data": []})
