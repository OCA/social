# Copyright 2026 Domatix <https://www.domatix.cloud>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from unittest.mock import patch

import requests

from odoo.exceptions import UserError
from odoo.tools import mute_logger

from .common import TikTokCommon

POST_ACCOUNT = "odoo.addons.social_media_tiktok.models.social_post_account"
ACCOUNT = "odoo.addons.social_media_tiktok.models.social_account.SocialAccount"
LOGGER = "odoo.addons.social_media_tiktok.models.social_post_account"
BASE_LOGGER = "odoo.addons.social_media_base.models.social_post_account"


class TestSocialPostAccountTikTok(TikTokCommon):
    """What a publication does on TikTok."""

    def test_remote_post_of_another_media(self):
        line = self._create_line(self.other_account)
        self.assertFalse(line._check_remote_post_exists())

    def test_remote_post_without_a_reference(self):
        line = self._create_line()
        self.assertTrue(line._check_remote_post_exists())

    @patch(f"{POST_ACCOUNT}.requests.post")
    def test_remote_post_exists(self, mock_post):
        line = self._create_line(remote_ref="video-id")
        mock_post.return_value = self._response({"data": {"videos": [{"id": "1"}]}})
        self.assertTrue(line._check_remote_post_exists())

    @patch(f"{POST_ACCOUNT}.requests.post")
    def test_remote_post_is_gone(self, mock_post):
        line = self._create_line(remote_ref="video-id")
        mock_post.return_value = self._response({"data": {"videos": []}})
        self.assertFalse(line._check_remote_post_exists())

    @patch(f"{POST_ACCOUNT}.requests.post")
    def test_remote_check_refused(self, mock_post):
        line = self._create_line(remote_ref="video-id")
        mock_post.return_value = self._response(None, 500)
        self.assertTrue(line._check_remote_post_exists())

    @mute_logger(LOGGER)
    @patch(f"{POST_ACCOUNT}.requests.post")
    def test_remote_check_without_connection(self, mock_post):
        line = self._create_line(remote_ref="video-id")
        mock_post.side_effect = requests.RequestException("down")
        self.assertTrue(line._check_remote_post_exists())

    def test_action_post_of_another_media(self):
        line = self._create_line(self.other_account)
        self.assertIsNone(line._action_post(line.post_id))

    @patch(f"{ACCOUNT}._post_tiktok_video", return_value=False)
    def test_action_post_private(self, mock_post):
        account = self._create_account()
        post = self._create_post(account, videos=self._video())
        post.action_create_post_account()
        line = post.post_account_ids
        self.assertEqual(line.state, "posted")
        self.assertFalse(line.remote_ref)
        self.assertIn("private", " ".join(line.message_ids.mapped("body")))

    @mute_logger(BASE_LOGGER)
    @patch(f"{ACCOUNT}._post_tiktok_video", return_value=None)
    def test_action_post_without_reference_is_refused(self, mock_post):
        account = self._create_account()
        post = self._create_post(account, videos=self._video())
        post.action_create_post_account()
        line = post.post_account_ids
        self.assertEqual(line.state, "failed")
        self.assertIn("did not return a reference", line.failed_description)

    @patch(f"{ACCOUNT}._delete_tiktok_video")
    def test_delete_post_account_of_tiktok(self, mock_delete):
        account = self._create_account()
        line = self._create_line(account, remote_ref="video-id")
        mock_delete.return_value = {"success": True, "message": ""}
        self.assertTrue(line._delete_post_account()["success"])
        mock_delete.assert_called_once_with(line)

    def test_delete_post_account_of_another_media(self):
        line = self._create_line(self.other_account)
        self.assertIsNone(line._delete_post_account())

    def test_comments_are_not_supported(self):
        self.assertFalse(self._create_line()._supports_comments())

    def test_comments_of_another_media(self):
        line = self._create_line(self.other_account)
        with self.assertRaises(UserError):
            line.get_comments()
