# Copyright 2026 Binhex <https://www.binhex.cloud>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import base64
from unittest.mock import patch

from .test_social_sync_common import TestSocialMediaSyncCommon, media_download_response

LOGGER_SYNC_POST_ACCOUNT = "odoo.addons.social_media_sync.models.social_post_account"
MEDIA_MAX_SIZE_PARAM = "social_media_sync.media_max_size_mb"
MEGABYTE = 1024 * 1024


class SizedBlock(bytes):
    """A block of a body that says it is larger than what it holds.

    The download counts the body with ``len()`` of each block, so a few bytes
    stand for a body of any size without holding it in the memory of the test.
    """

    def __new__(cls, content, size):
        block = super().__new__(cls, content)
        block.size = size
        return block

    def __len__(self):
        return self.size


class TestMediaDownloadSync(TestSocialMediaSyncCommon):
    """The download of a media of the social media, and its cap."""

    def _set_max_size(self, value):
        """Write the cap parameter as an administrator would."""
        self.env["ir.config_parameter"].sudo().set_param(MEDIA_MAX_SIZE_PARAM, value)

    def _download(self, response, ref="urn:li:image:1"):
        """Download a media answered by ``response``.

        :return: the attachment created and the mock of ``requests.get``.
        :rtype: tuple
        """
        with patch("requests.get", return_value=response) as mock_get:
            attachment = self.social_post_account_id._map_medias_account(
                name=ref, url=f"https://cdn.example.com/{ref}?signature=secret"
            )
        return attachment, mock_get

    def test_the_parameter_ships_at_one_hundred_megabytes(self):
        """The module writes the cap so that it can be found and raised."""
        self.assertEqual(
            self.env["ir.config_parameter"].sudo().get_param(MEDIA_MAX_SIZE_PARAM),
            "100",
        )
        self.assertEqual(self.SocialPostAccount._media_max_size_bytes(), 100 * MEGABYTE)

    def test_the_attachment_holds_the_content_and_not_the_url(self):
        """The URL of the social media is only used to download."""
        attachment, mock_get = self._download(
            media_download_response(chunks=[b"fake ", b"image"])
        )
        self.assertEqual(attachment.datas, base64.b64encode(b"fake image"))
        self.assertFalse(attachment.url)
        self.assertEqual(attachment.name, "urn:li:image:1")
        self.assertIs(mock_get.call_args.kwargs["stream"], True)

    def test_a_content_length_above_the_cap_reads_no_body(self):
        """The size the answer says is enough to leave the media out."""
        self._set_max_size("1")
        response = media_download_response(
            chunks=[b"never read"], headers={"Content-Length": str(2 * MEGABYTE)}
        )
        with self.assertLogs(LOGGER_SYNC_POST_ACCOUNT, "WARNING"):
            attachment, _mock_get = self._download(response)
        self.assertFalse(attachment)
        response.iter_content.assert_not_called()
        self.assertFalse(
            self.social_post_account_id._get_medias_account(["urn:li:image:1"])
        )

    def test_a_body_above_the_cap_without_content_length_is_left_out(self):
        """What the answer does not say is counted while it is read."""
        self._set_max_size("1")
        response = media_download_response(
            chunks=[SizedBlock(b"a", MEGABYTE), SizedBlock(b"b", MEGABYTE)]
        )
        with self.assertLogs(LOGGER_SYNC_POST_ACCOUNT, "WARNING"):
            attachment, _mock_get = self._download(response)
        self.assertFalse(attachment)

    def test_a_cap_at_zero_downloads_any_size(self):
        """Zero is no cap, even for a body above the size the module ships."""
        self._set_max_size("0")
        response = media_download_response(
            chunks=[SizedBlock(b"a", 60 * MEGABYTE), SizedBlock(b"b", 60 * MEGABYTE)]
        )
        attachment, _mock_get = self._download(response)
        self.assertEqual(attachment.datas, base64.b64encode(b"ab"))

    def test_a_cap_that_is_not_a_number_falls_back_to_the_default(self):
        """A typo does not remove the protection."""
        self._set_max_size("one hundred")
        with self.assertLogs(LOGGER_SYNC_POST_ACCOUNT, "WARNING"):
            self.assertEqual(
                self.SocialPostAccount._media_max_size_bytes(), 100 * MEGABYTE
            )

    def test_an_empty_cap_is_no_cap(self):
        """An empty value is read as no cap, and says nothing about it."""
        self._set_max_size("")
        with self.assertNoLogs(LOGGER_SYNC_POST_ACCOUNT, "WARNING"):
            self.assertEqual(self.SocialPostAccount._media_max_size_bytes(), 0)

    def test_a_negative_cap_is_no_cap(self):
        """A negative size caps nothing, the same as zero."""
        self._set_max_size("-5")
        self.assertEqual(self.SocialPostAccount._media_max_size_bytes(), 0)
