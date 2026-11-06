# Copyright 2026 Domatix <https://www.domatix.cloud>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from unittest.mock import patch

import requests

from odoo.exceptions import UserError
from odoo.tools import mute_logger

from .common import YouTubeCommon

POST_ACCOUNT = "odoo.addons.social_media_youtube.models.social_post_account"
ACCOUNT = "odoo.addons.social_media_youtube.models.social_account.SocialAccount"
LOGGER = "odoo.addons.social_media_youtube.models.social_post_account"
BASE_LOGGER = "odoo.addons.social_media_base.models.social_post_account"


class TestSocialPostAccountYouTube(YouTubeCommon):
    """Publishing, comments and deletion on a YouTube publication."""

    def test_action_post_of_another_media(self):
        line = self._create_line(self.other_account)
        self.assertIsNone(line._action_post(line.post_id))

    @patch(f"{ACCOUNT}._post_youtube_video", return_value="video-id")
    def test_action_post_publishes_the_line(self, mock_post):
        account = self._create_account()
        post = self._create_post(account, videos=self._video())
        post.action_create_post_account()
        line = post.post_account_ids
        self.assertEqual(line.state, "posted")
        self.assertEqual(line.remote_ref, "video-id")
        self.assertEqual(
            line.post_account_url, "https://www.youtube.com/watch?v=video-id"
        )

    @mute_logger(BASE_LOGGER)
    @patch(f"{ACCOUNT}._post_youtube_video", return_value=None)
    def test_action_post_without_reference_is_refused(self, mock_post):
        account = self._create_account()
        post = self._create_post(account, videos=self._video())
        post.action_create_post_account()
        line = post.post_account_ids
        self.assertEqual(line.state, "failed")
        self.assertIn("did not return a reference", line.failed_description)

    @patch(f"{ACCOUNT}._delete_youtube_video")
    def test_delete_post_account_of_youtube(self, mock_delete):
        account = self._create_account()
        line = self._create_line(account, remote_ref="video-id")
        mock_delete.return_value = {"success": True, "message": ""}
        self.assertTrue(line._delete_post_account()["success"])
        mock_delete.assert_called_once_with(line)

    def test_delete_post_account_of_another_media(self):
        line = self._create_line(self.other_account)
        self.assertIsNone(line._delete_post_account())

    def test_comments_are_supported(self):
        self.assertTrue(self._create_line()._supports_comments())
        self.assertFalse(self._create_line(self.other_account)._supports_comments())

    @patch(f"{POST_ACCOUNT}.requests.get")
    def test_get_comments(self, mock_get):
        account = self._create_account()
        line = self._create_line(account, remote_ref="video-id")
        mock_get.return_value = self._response(
            {
                "items": [
                    {
                        "snippet": {
                            "topLevelComment": {
                                "id": "comment-1",
                                "snippet": {
                                    "textOriginal": "hello",
                                    "authorDisplayName": "Ada",
                                    "authorProfileImageUrl": "https://cdn/ada",
                                    "publishedAt": "2026-01-01T00:00:00Z",
                                },
                            }
                        }
                    }
                ]
            }
        )
        result = line.get_comments()
        self.assertTrue(result["success"])
        self.assertEqual(
            result["data"],
            [
                {
                    "id": "comment-1",
                    "text": "hello",
                    "actor": "Ada",
                    "author_image": "https://cdn/ada",
                    "published_time": "2026-01-01T00:00:00Z",
                    "images_url": [],
                }
            ],
        )

    @patch(f"{POST_ACCOUNT}.requests.get")
    def test_get_comments_follow_pagination(self, mock_get):
        account = self._create_account()
        line = self._create_line(account, remote_ref="video-id")
        mock_get.side_effect = [
            self._response({"items": [{"snippet": {}}], "nextPageToken": "next"}),
            self._response({"items": [{"snippet": {}}]}),
        ]
        result = line.get_comments()
        self.assertEqual(len(result["data"]), 2)
        self.assertEqual(mock_get.call_count, 2)

    @patch(f"{POST_ACCOUNT}.requests.get")
    def test_get_comments_stops_after_the_last_page(self, mock_get):
        account = self._create_account()
        line = self._create_line(account, remote_ref="video-id")
        mock_get.side_effect = [
            self._response({"items": [{"snippet": {}}], "nextPageToken": "next"})
            for _index in range(10)
        ]
        result = line.get_comments()
        self.assertEqual(len(result["data"]), 10)
        self.assertEqual(mock_get.call_count, 10)

    @mute_logger(LOGGER)
    @patch(f"{POST_ACCOUNT}.requests.get")
    def test_get_comments_refused(self, mock_get):
        account = self._create_account()
        line = self._create_line(account, remote_ref="video-id")
        mock_get.return_value = self._response(None, 500, text="no comments")
        result = line.get_comments()
        self.assertFalse(result["success"])
        self.assertIn("no comments", result["message"])

    @mute_logger(LOGGER)
    @patch(f"{POST_ACCOUNT}.requests.get")
    def test_get_comments_without_connection(self, mock_get):
        account = self._create_account()
        line = self._create_line(account, remote_ref="video-id")
        mock_get.side_effect = requests.RequestException("down")
        result = line.get_comments()
        self.assertFalse(result["success"])
        self.assertIn("down", result["message"])

    def test_get_comments_of_another_media(self):
        line = self._create_line(self.other_account)
        with self.assertRaises(UserError):
            line.get_comments()

    @patch(f"{POST_ACCOUNT}.requests.post")
    def test_create_comment(self, mock_post):
        account = self._create_account()
        line = self._create_line(account, remote_ref="video-id")
        mock_post.return_value = self._response(
            {"snippet": {"topLevelComment": {"id": "comment-1"}}}, status_code=201
        )
        result = line.create_comment({"body": "hello"})
        self.assertEqual(result, {"success": True, "id": "comment-1"})
        self.assertEqual(
            mock_post.call_args.kwargs["json"]["snippet"]["topLevelComment"]["snippet"][
                "textOriginal"
            ],
            "hello",
        )

    @mute_logger(LOGGER)
    @patch(f"{POST_ACCOUNT}.requests.post")
    def test_create_comment_refused(self, mock_post):
        account = self._create_account()
        line = self._create_line(account, remote_ref="video-id")
        mock_post.return_value = self._response(None, 500, text="no comment")
        result = line.create_comment({"body": "hello"})
        self.assertFalse(result["success"])
        self.assertIn("no comment", result["message"])

    @mute_logger(LOGGER)
    @patch(f"{POST_ACCOUNT}.requests.post")
    def test_create_comment_without_connection(self, mock_post):
        account = self._create_account()
        line = self._create_line(account, remote_ref="video-id")
        mock_post.side_effect = requests.RequestException("down")
        result = line.create_comment({"body": "hello"})
        self.assertFalse(result["success"])
        self.assertIn("down", result["message"])

    def test_create_comment_of_another_media(self):
        line = self._create_line(self.other_account)
        with self.assertRaises(UserError):
            line.create_comment({"body": "hello"})

    @patch(f"{POST_ACCOUNT}.requests.delete")
    def test_delete_comment(self, mock_delete):
        account = self._create_account()
        line = self._create_line(account, remote_ref="video-id")
        mock_delete.return_value = self._response({}, status_code=204)
        self.assertTrue(line.delete_youtube_comment("comment-1")["success"])

    @mute_logger(LOGGER)
    @patch(f"{POST_ACCOUNT}.requests.delete")
    def test_delete_comment_refused(self, mock_delete):
        account = self._create_account()
        line = self._create_line(account, remote_ref="video-id")
        mock_delete.return_value = self._response(None, 500, text="no delete")
        result = line.delete_youtube_comment("comment-1")
        self.assertFalse(result["success"])
        self.assertIn("no delete", result["message"])

    @mute_logger(LOGGER)
    @patch(f"{POST_ACCOUNT}.requests.delete")
    def test_delete_comment_without_connection(self, mock_delete):
        account = self._create_account()
        line = self._create_line(account, remote_ref="video-id")
        mock_delete.side_effect = requests.RequestException("down")
        result = line.delete_youtube_comment("comment-1")
        self.assertFalse(result["success"])
        self.assertIn("down", result["message"])
