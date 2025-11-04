# Copyright 2025 Binhex <https://www.binhex.cloud>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from unittest.mock import MagicMock, patch

from odoo.addons.social_media_base.tests.test_social_common import (
    PATCH_POST_ACCOUNT,
)
from odoo.addons.social_media_x.tests.test_common_x import (
    TestSocialCommonX,
)

from .test_common_x import PATCH_ACCOUNT_X


class TestSocialPostAccountX(TestSocialCommonX):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

    @patch(PATCH_POST_ACCOUNT.format("filter_by_media_types"))
    @patch(PATCH_ACCOUNT_X.format("SocialAccount.create_tweet"))
    def test_action_post(self, mock_create_tweet, mock_filter_by_media_types):
        mock_filter_by_media_types.return_value = [MagicMock()]
        mock_create_post_data = MagicMock()
        mock_create_post_data.return_value = "159753456"
        mock_create_tweet.return_value = mock_create_post_data
        self.social_post_account_id._action_post()
        self.assertGreaterEqual(
            self.SocialPostAccount.search_count(
                [
                    ("x_post_account_id", "=", "159753456"),
                    (
                        "post_account_url",
                        "=",
                        "https://x.com/fake-username/status/159753456",
                    ),
                ]
            ),
            0,
        )
        self.assertEqual(
            mock_filter_by_media_types.call_count,
            1,
        )

    def test_create_x_comment(self):
        mock_client = MagicMock()
        with (
            patch.object(
                type(self.SocialAccountX), "get_client_api", return_value=mock_client
            ) as mock_get_client_api,
            patch.object(
                type(self.SocialAccountX),
                "_prepare_medias_for_tweet",
                return_value=mock_client,
            ) as mock_medias_for_tweet,
        ):
            post_data = {
                "body": "Test Comment",
                "attachment_ids": [1],
            }
            self.SocialPostAccountX.create_x_comment(post_data)
            mock_medias_for_tweet.assert_called_once()
            self.assertEqual(mock_get_client_api.call_count, 1)

    def test_create_comment(self):
        mock_client = MagicMock()
        with patch.object(
            type(self.SocialPostAccountX), "create_x_comment", return_value=mock_client
        ) as mock_create_comment:
            post_data = {
                "body": "Test Comment",
                "attachment_ids": [1],
            }
            self.SocialPostAccountX.create_comment(post_data)
            mock_create_comment.assert_called_once()
