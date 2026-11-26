# Copyright 2026 Domatix <https://www.domatix.cloud>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from unittest.mock import patch

from .common import InstagramCommon

POST = "odoo.addons.social_media_instagram.models.social_post"


class TestSocialPostInstagram(InstagramCommon):
    """The limits Instagram imposes on a post."""

    def test_other_media_is_left_to_its_connector(self):
        post = self._create_post(message="Anything")
        self.assertFalse(post._get_post_errors("other"))

    def test_caption_too_long(self):
        post = self._create_post(message="x" * 2201, images=self._attachment())
        errors = post._get_post_errors("instagram")
        self.assertTrue(any("2200" in error for error in errors))

    def test_media_is_required(self):
        post = self._create_post(message="No media")
        errors = post._get_post_errors("instagram")
        self.assertTrue(any("At least one image" in error for error in errors))

    def test_too_many_images(self):
        images = self.env["ir.attachment"]
        for index in range(11):
            images |= self._attachment(f"{index}.jpg")
        post = self._create_post(message="Too many", images=images)
        errors = post._get_post_errors("instagram")
        self.assertTrue(any("at most 10 images" in error for error in errors))

    def test_image_must_be_jpeg(self):
        post = self._create_post(
            message="PNG", images=self._attachment("photo.png", mimetype="image/png")
        )
        errors = post._get_post_errors("instagram")
        self.assertTrue(any("not a JPEG image" in error for error in errors))

    @patch(f"{POST}._MAX_IMAGE_SIZE_INSTAGRAM", 1)
    def test_image_must_be_small_enough(self):
        post = self._create_post(message="Big", images=self._attachment())
        errors = post._get_post_errors("instagram")
        self.assertTrue(any("larger than" in error for error in errors))
