# Copyright 2026 Binhex <https://www.binhex.cloud>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo.tests.common import tagged

from ..social_x_sync_utils import _strip_media_links_x
from .test_sync_x_common import TestSocialSyncCommonX

MEDIA_LINK_X = "https://t.co/media"
AUTHOR_LINK_X = "https://t.co/author"


@tagged("post_install", "-at_install")
class TestSocialSyncUtilsX(TestSocialSyncCommonX):
    """Only the links X adds for the media leave the text of a tweet."""

    def test_strip_media_links_removes_the_link_of_a_media(self):
        entities = {"urls": [{"url": MEDIA_LINK_X, "media_key": "3_1"}]}
        self.assertEqual(
            _strip_media_links_x(f"A photo {MEDIA_LINK_X}", entities), "A photo "
        )

    def test_strip_media_links_keeps_a_link_the_author_wrote(self):
        entities = {"urls": [{"url": AUTHOR_LINK_X}]}
        text = f"Read this {AUTHOR_LINK_X}"
        self.assertEqual(_strip_media_links_x(text, entities), text)

    def test_strip_media_links_removes_only_the_media_one(self):
        entities = {
            "urls": [
                {"url": AUTHOR_LINK_X},
                {"url": MEDIA_LINK_X, "media_key": "3_1"},
            ]
        }
        self.assertEqual(
            _strip_media_links_x(f"Read this {AUTHOR_LINK_X} {MEDIA_LINK_X}", entities),
            f"Read this {AUTHOR_LINK_X} ",
        )

    def test_strip_media_links_without_urls_returns_the_text(self):
        text = f"A photo {MEDIA_LINK_X}"
        for entities in (None, {}, {"mentions": [{"username": "someone"}]}):
            self.assertEqual(_strip_media_links_x(text, entities), text)
