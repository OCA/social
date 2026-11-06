# Copyright 2026 Domatix <https://www.domatix.cloud>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from .common import YouTubeCommon


class TestSocialPostYouTube(YouTubeCommon):
    """The YouTube requirements on a post."""

    def test_other_media_is_left_to_its_connector(self):
        post = self._create_post()
        self.assertFalse(post._get_post_errors("other"))

    def test_video_is_required(self):
        post = self._create_post()
        self.assertTrue(post._get_post_errors("youtube"))

    def test_video_is_enough(self):
        post = self._create_post(videos=self._video())
        self.assertFalse(post._get_post_errors("youtube"))

    def test_privacy_defaults_to_private(self):
        self.assertEqual(self._create_post().youtube_privacy_status, "private")

    def test_has_youtube_account(self):
        account = self._create_account()
        post = self._create_post(account)
        self.assertTrue(post.has_youtube_account)
        other = self._create_post(self.other_account)
        self.assertFalse(other.has_youtube_account)
