# Copyright 2026 Domatix <https://www.domatix.cloud>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from .common import TikTokCommon


class TestSocialPostTikTok(TikTokCommon):
    """The TikTok requirements on a post."""

    def test_other_media_is_left_to_its_connector(self):
        post = self._create_post()
        self.assertFalse(post._get_post_errors("other"))

    def test_video_is_required(self):
        post = self._create_post()
        self.assertTrue(post._get_post_errors("tiktok"))

    def test_video_is_enough(self):
        post = self._create_post(videos=self._video())
        self.assertFalse(post._get_post_errors("tiktok"))

    def test_images_are_ignored_when_the_video_goes_out(self):
        post = self._create_post(images=self._image(), videos=self._video())
        warnings = post._get_post_warnings("tiktok")
        self.assertTrue(any("images will be ignored" in text for text in warnings))

    def test_no_warning_without_images(self):
        post = self._create_post(videos=self._video())
        self.assertFalse(post._get_post_warnings("tiktok"))

    def test_no_warning_for_another_media(self):
        post = self._create_post(images=self._image(), videos=self._video())
        self.assertFalse(post._get_post_warnings("other"))
