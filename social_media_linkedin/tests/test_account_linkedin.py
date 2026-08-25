# Copyright 2026 Binhex <https://www.binhex.cloud>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).


from contextlib import contextmanager
from datetime import date, datetime, timedelta
from unittest.mock import MagicMock, Mock, patch

import psycopg2
from dateutil.relativedelta import relativedelta
from psycopg2 import errorcodes

from odoo import _, fields
from odoo.exceptions import UserError
from odoo.fields import Command
from odoo.tests.common import tagged
from odoo.tools import mute_logger

from odoo.addons.social_media_base.exceptions import SocialCredentialsError
from odoo.addons.social_media_base.tests.test_social_common import (
    PATCH_ACCOUNT,
    PATCH_SOCIAL_BASE_MIXIN,
    PATCH_WIZARD_ACCOUNT,
)
from odoo.addons.social_media_linkedin.social_linkedin_utils import (
    _POSTS_MAX_PAGES_LINKEDIN,
    _QUERY_STRING_MARGIN_BYTES_LINKEDIN,
    _QUERY_STRING_MAX_BYTES_LINKEDIN,
    _STATISTICS_HISTORY_MONTHS_LINKEDIN,
    _TOKEN_MARGIN_DAYS_LINKEDIN,
    _UPDATE_CHECK_DAYS_LINKEDIN,
    _batch_urns_by_url_size,
    _encoded_urns_bytes,
    epoch_milliseconds,
    social_url_encode,
)
from odoo.addons.social_media_linkedin.tests.test_common_linkedin import (
    PATCH_ACCOUNT_LINKEDIN,
    PATCH_POST_ACCOUNT_LINKEDIN,
    PATCH_WIZARD_ACCOUNT_LINKEDIN,
    TestSocialCommonLinkedin,
)

LOGGER_ACCOUNT_LINKEDIN = "odoo.addons.social_media_linkedin.models.social_account"


def _linkedin_day(offset):
    """Return the ISO day ``offset`` days back from today.

    The check trims the buckets to ``_linkedin_check_days``, so the fixtures
    move with the calendar instead of naming a fixed day that would fall out
    of the window as soon as it went past.
    """
    return (fields.Date.today() - timedelta(days=offset)).isoformat()


def _linkedin_buckets(statistics):
    """Return the watched figures as the buckets the finder answers.

    ``_get_linkedin_daily_statistics`` builds six figures per day and the
    check keeps five. The engagement is put back as a ratio of its own, so a
    figure leaking through would be caught by its value.
    """
    return {
        day: (clicks, likes, comments, shares, 0.5, impressions)
        for day, (
            clicks,
            likes,
            comments,
            shares,
            impressions,
        ) in statistics.items()
    }


# The figures LinkedIn reports for a whole page day by day, which the check for
# updates watches instead of reading the statistics of every publication. Every
# bucket is (clicks, likes, comments, shares, impressions), the engagement left
# out. Taken from a real account, with its days moved onto the window the check
# compares.
RECENT_STATISTICS_LINKEDIN = {
    _linkedin_day(3): (0, 0, 0, 0, 17),
    _linkedin_day(2): (5, 0, 0, 0, 29),
    _linkedin_day(1): (0, 1, 0, 0, 0),
}


@tagged("post_install", "-at_install")
class TestSocialLinkedin(TestSocialCommonLinkedin):
    """Users are created here, so every module has to be in the registry."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.video_mock = type("Video", (), {"datas": cls.video_data})()
        cls.image_mock = type("Image", (), {"datas": cls.image_base64})()
        cls.media_image = "urn:li:image:{}"
        cls.media_video = "urn:li:video:{}"

    def test_linkedin_prepare_url_upload_image(self):
        fake_response = {
            "value": {
                "image": self.media_image.format("C123456"),
                "uploadUrl": "https://fake.upload.url/image",
            }
        }

        patch_request_linkedin = self.get_patch_exceptions_linkedin(fake_response)

        with patch_request_linkedin as mock_request:
            (
                image,
                upload_url,
            ) = self.SocialAccountLinkedin._linkedin_prepare_url_upload_image()

            self.assertEqual(image, self.media_image.format("C123456"))
            self.assertEqual(upload_url, "https://fake.upload.url/image")

            mock_request.assert_called_once()
            self.assertEqual(
                mock_request.call_args.kwargs["params_values"],
                {"action": "initializeUpload"},
            )

    def test_linkedin_prepare_url_upload_image_error(self):
        """An answer that is not the registered upload stops the publication."""
        mock_response = self.generate_magic_mock(**{"status_code": 403})
        with self.get_patch_exceptions_linkedin(mock_response):
            with self.assertRaises(UserError) as context:
                self.SocialAccountLinkedin._linkedin_prepare_url_upload_image()
        self.assertIn("could not be uploaded to LinkedIn", str(context.exception))

    def test_linkedin_prepare_images_for_post_success(self):
        """Every image is registered and uploaded, and its URN is kept."""
        patch_upload_url = patch.object(
            type(self.SocialAccountLinkedin),
            "_linkedin_prepare_url_upload_image",
            return_value=(
                self.media_image.format("XYZ"),
                "https://fake.upload/image",
            ),
        )
        mock_response = self.generate_magic_mock(**{"status_code": 201})
        with patch_upload_url, self.get_patch_exceptions_linkedin(
            mock_response
        ) as mock_request:
            images = self.SocialAccountLinkedin._linkedin_prepare_images_for_post(
                image_ids=[self.image_mock]
            )
        self.assertEqual(images, [self.media_image.format("XYZ")])
        self.assertEqual(mock_request.call_args.kwargs["method"], "PUT")
        self.assertEqual(
            mock_request.call_args.kwargs["complete_url"], "https://fake.upload/image"
        )
        self.assertEqual(mock_request.call_args.kwargs["data"], b"testimage")

    def test_linkedin_prepare_images_for_post_upload_error(self):
        patch_upload_url = patch.object(
            type(self.SocialAccountLinkedin),
            "_linkedin_prepare_url_upload_image",
            return_value=(
                self.media_image.format("XYZ"),
                "https://fake.upload/image",
            ),
        )
        mock_response = self.generate_magic_mock(**{"status_code": 400})
        with patch_upload_url, self.get_patch_exceptions_linkedin(mock_response):
            with self.assertRaises(UserError) as context:
                self.SocialAccountLinkedin._linkedin_prepare_images_for_post(
                    image_ids=[self.image_mock]
                )
        self.assertIn("could not be uploaded to LinkedIn", str(context.exception))

    def test_initialize_video_upload(self):
        fake_response = {
            "value": {
                "video": self.media_video.format("VID123"),
                "uploadInstructions": [
                    {
                        "uploadUrl": "https://fake.upload/video/1",
                        "firstByte": 0,
                        "lastByte": 3,
                    }
                ],
                "uploadToken": "token-123",
            }
        }
        with self.get_patch_exceptions_linkedin(fake_response) as mock_request:
            (
                video,
                instructions,
                token,
            ) = self.SocialAccountLinkedin._linkedin_initialize_video_upload(4)
        self.assertEqual(video, self.media_video.format("VID123"))
        self.assertEqual(len(instructions), 1)
        self.assertEqual(token, "token-123")
        json_data = mock_request.call_args.kwargs["json_data"]
        self.assertEqual(json_data["initializeUploadRequest"]["fileSizeBytes"], 4)

    def test_initialize_video_upload_error(self):
        mock_response = self.generate_magic_mock(**{"status_code": 400})
        with self.get_patch_exceptions_linkedin(mock_response):
            with self.assertRaises(UserError) as context:
                self.SocialAccountLinkedin._linkedin_initialize_video_upload(4)
        self.assertIn("could not be uploaded to LinkedIn", str(context.exception))

    def test_upload_video_parts_keeps_the_order_of_the_etags(self):
        """Each part carries its own slice and its ETag keeps its position."""
        instructions = [
            {"uploadUrl": "https://fake.upload/video/1", "firstByte": 0, "lastByte": 3},
            {"uploadUrl": "https://fake.upload/video/2", "firstByte": 4, "lastByte": 8},
        ]
        first_part = self.generate_magic_mock(**{"status_code": 201})
        first_part.headers = {"etag": '"etag-1"'}
        second_part = self.generate_magic_mock(**{"status_code": 201})
        second_part.headers = {"etag": '"etag-2"'}
        patch_request = self.get_patch_exceptions_linkedin(
            side_effect=[first_part, second_part]
        )
        with patch_request as mock_request:
            part_ids = self.SocialAccountLinkedin._linkedin_upload_video_parts(
                b"123456789", instructions
            )
        self.assertEqual(part_ids, ["etag-1", "etag-2"])
        self.assertEqual(mock_request.call_args_list[0].kwargs["data"], b"1234")
        self.assertEqual(mock_request.call_args_list[1].kwargs["data"], b"56789")

    def test_upload_video_parts_without_etag(self):
        """A part without ETag is caught here, not inside finalizeUpload."""
        instructions = [
            {"uploadUrl": "https://fake.upload/video/1", "firstByte": 0, "lastByte": 3},
            {"uploadUrl": "https://fake.upload/video/2", "firstByte": 4, "lastByte": 8},
        ]
        first_part = self.generate_magic_mock(**{"status_code": 201})
        first_part.headers = {"etag": '"etag-1"'}
        second_part = self.generate_magic_mock(**{"status_code": 201})
        second_part.headers = {}
        patch_request = self.get_patch_exceptions_linkedin(
            side_effect=[first_part, second_part]
        )
        with patch_request, self.assertRaises(UserError) as context:
            self.SocialAccountLinkedin._linkedin_upload_video_parts(
                b"123456789", instructions
            )
        self.assertIn("did not return the identifier", str(context.exception))
        self.assertIn("part 2 of 2", str(context.exception))

    def test_upload_video_parts_multipart_slices(self):
        """Every part carries exactly the bytes of its own instruction."""
        part_size = 4 * 1024 * 1024
        video_data = b"\x00" * (part_size * 2 + 512)
        instructions = [
            {
                "uploadUrl": f"https://fake.upload/video/{number}",
                "firstByte": number * part_size,
                "lastByte": min(len(video_data), (number + 1) * part_size) - 1,
            }
            for number in range(3)
        ]
        parts = []
        for number in range(3):
            part = self.generate_magic_mock(**{"status_code": 201})
            part.headers = {"etag": f'"etag-{number}"'}
            parts.append(part)
        with self.get_patch_exceptions_linkedin(side_effect=parts) as mock_request:
            part_ids = self.SocialAccountLinkedin._linkedin_upload_video_parts(
                video_data, instructions
            )
        self.assertEqual(part_ids, ["etag-0", "etag-1", "etag-2"])
        self.assertEqual(len(mock_request.call_args_list), 3)
        self.assertEqual(
            [len(call.kwargs["data"]) for call in mock_request.call_args_list],
            [part_size, part_size, 512],
        )

    def test_upload_video_parts_error(self):
        instructions = [
            {"uploadUrl": "https://fake.upload/video/1", "firstByte": 0, "lastByte": 3}
        ]
        mock_response = self.generate_magic_mock(**{"status_code": 400})
        with self.get_patch_exceptions_linkedin(mock_response):
            with self.assertRaises(UserError) as context:
                self.SocialAccountLinkedin._linkedin_upload_video_parts(
                    b"1234", instructions
                )
        self.assertIn("could not be uploaded to LinkedIn", str(context.exception))

    def test_finalize_video_upload(self):
        mock_response = self.generate_magic_mock(**{"status_code": 200})
        with self.get_patch_exceptions_linkedin(mock_response) as mock_request:
            self.SocialAccountLinkedin._linkedin_finalize_video_upload(
                self.media_video.format("VID123"), "token-123", ["etag-1"]
            )
        json_data = mock_request.call_args.kwargs["json_data"]
        self.assertEqual(
            json_data["finalizeUploadRequest"]["uploadedPartIds"], ["etag-1"]
        )

    def test_finalize_video_upload_error(self):
        mock_response = self.generate_magic_mock(**{"status_code": 400})
        with self.get_patch_exceptions_linkedin(mock_response):
            with self.assertRaises(UserError) as context:
                self.SocialAccountLinkedin._linkedin_finalize_video_upload(
                    self.media_video.format("VID123"), "token-123", ["etag-1"]
                )
        self.assertIn("could not be uploaded to LinkedIn", str(context.exception))

    def test_wait_video_available(self):
        """The video is polled until LinkedIn finishes processing it."""
        processing = self.generate_magic_mock(
            **{"status_code": 200, "json_return_value": {"status": "PROCESSING"}}
        )
        available = self.generate_magic_mock(
            **{"status_code": 200, "json_return_value": {"status": "AVAILABLE"}}
        )
        patch_request = self.get_patch_exceptions_linkedin(
            side_effect=[processing, available]
        )
        with patch_request as mock_request, patch(
            f"{LOGGER_ACCOUNT_LINKEDIN}.time.sleep"
        ) as mock_sleep:
            self.assertTrue(
                self.SocialAccountLinkedin._linkedin_wait_video_available(
                    self.media_video.format("VID123")
                )
            )
        self.assertEqual(mock_request.call_count, 2)
        mock_sleep.assert_called_once()

    def test_wait_video_available_processing_failed(self):
        failed = self.generate_magic_mock(
            **{
                "status_code": 200,
                "json_return_value": {
                    "status": "PROCESSING_FAILED",
                    "processingFailureReason": "UNSUPPORTED_FORMAT",
                },
            }
        )
        with self.get_patch_exceptions_linkedin(failed):
            with self.assertRaises(UserError) as context:
                self.SocialAccountLinkedin._linkedin_wait_video_available(
                    self.media_video.format("VID123")
                )
        self.assertIn("UNSUPPORTED_FORMAT", str(context.exception))

    def test_wait_video_available_timeout(self):
        """A video that never becomes available stops the publication."""
        self.env["ir.config_parameter"].sudo().set_param(
            "social_media_linkedin.video_poll_attempts", "2"
        )
        self.env["ir.config_parameter"].sudo().set_param(
            "social_media_linkedin.video_poll_delay", "0"
        )
        processing = self.generate_magic_mock(
            **{"status_code": 200, "json_return_value": {"status": "PROCESSING"}}
        )
        with self.get_patch_exceptions_linkedin(processing) as mock_request, patch(
            f"{LOGGER_ACCOUNT_LINKEDIN}.time.sleep"
        ):
            with self.assertRaises(UserError) as context:
                self.SocialAccountLinkedin._linkedin_wait_video_available(
                    self.media_video.format("VID123")
                )
        self.assertEqual(mock_request.call_count, 2)
        self.assertIn("still processing the video", str(context.exception))

    def test_wait_video_available_error(self):
        mock_response = self.generate_magic_mock(**{"status_code": 404})
        with self.get_patch_exceptions_linkedin(mock_response):
            with self.assertRaises(UserError) as context:
                self.SocialAccountLinkedin._linkedin_wait_video_available(
                    self.media_video.format("VID123")
                )
        self.assertIn("status of the video could not be read", str(context.exception))

    def test_video_poll_settings_fall_back_on_a_wrong_parameter(self):
        self.env["ir.config_parameter"].sudo().set_param(
            "social_media_linkedin.video_poll_attempts", "not a number"
        )
        attempts, delay = self.SocialAccountLinkedin._linkedin_video_poll_settings()
        self.assertEqual(attempts, 30)
        self.assertEqual(delay, 2)

    def test_linkedin_prepare_videos_for_post_success(self):
        """A video is uploaded by parts and published once it is available."""
        patch_initialize = patch.object(
            type(self.SocialAccountLinkedin),
            "_linkedin_initialize_video_upload",
            return_value=(self.media_video.format("VID123"), [{}], "token-123"),
        )
        patch_parts = patch.object(
            type(self.SocialAccountLinkedin),
            "_linkedin_upload_video_parts",
            return_value=["etag-1"],
        )
        patch_finalize = patch.object(
            type(self.SocialAccountLinkedin),
            "_linkedin_finalize_video_upload",
            return_value=None,
        )
        patch_wait = patch.object(
            type(self.SocialAccountLinkedin),
            "_linkedin_wait_video_available",
            return_value=True,
        )
        with patch_initialize, patch_parts, patch_finalize as mock_finalize, patch_wait:
            videos = self.SocialAccountLinkedin._linkedin_prepare_videos_for_post(
                video_ids=[self.video_mock]
            )
        self.assertEqual(videos, [self.media_video.format("VID123")])
        mock_finalize.assert_called_once_with(
            self.media_video.format("VID123"), "token-123", ["etag-1"]
        )

    def _patch_media_uploads(self, image_urns=None, video_urns=None):
        return (
            patch.object(
                type(self.SocialAccountLinkedin),
                "_linkedin_prepare_images_for_post",
                return_value=image_urns or [],
            ),
            patch.object(
                type(self.SocialAccountLinkedin),
                "_linkedin_prepare_videos_for_post",
                return_value=video_urns or [],
            ),
        )

    def _linkedin_create_post_payload(self, image_urns=None, video_urns=None):
        """Publish a post and return the body sent to the Posts API."""
        patch_images, patch_videos = self._patch_media_uploads(image_urns, video_urns)
        mock_response = self.generate_magic_mock(**{"status_code": 201})
        mock_response.headers = {"x-restli-id": "urn:li:share:1"}
        with patch_images, patch_videos, self.get_patch_exceptions_linkedin(
            mock_response
        ) as mock_request:
            post_urn, published_urns = self.SocialAccountLinkedin._linkedin_create_post(
                message="Hello", image_ids=[], video_ids=[]
            )
        self.assertEqual(post_urn, "urn:li:share:1")
        self.assertEqual(published_urns, image_urns or [])
        self.assertEqual(mock_request.call_args.kwargs["endpoint"], "/posts")
        return mock_request.call_args.kwargs["json_data"]

    def test_linkedin_create_post_text(self):
        json_data = self._linkedin_create_post_payload()
        self.assertEqual(json_data["commentary"], "Hello")
        self.assertEqual(json_data["visibility"], "PUBLIC")
        self.assertEqual(json_data["lifecycleState"], "PUBLISHED")
        self.assertNotIn("content", json_data)

    def test_linkedin_create_post_single_image(self):
        json_data = self._linkedin_create_post_payload(
            image_urns=[self.media_image.format("1")]
        )
        self.assertEqual(
            json_data["content"], {"media": {"id": self.media_image.format("1")}}
        )

    def test_linkedin_create_post_multi_image(self):
        json_data = self._linkedin_create_post_payload(
            image_urns=[self.media_image.format("1"), self.media_image.format("2")]
        )
        self.assertEqual(
            json_data["content"],
            {
                "multiImage": {
                    "images": [
                        {"id": self.media_image.format("1")},
                        {"id": self.media_image.format("2")},
                    ]
                }
            },
        )

    def test_linkedin_create_post_video_wins_over_the_images(self):
        """A post carrying a video does not even upload its images."""
        patch_images, patch_videos = self._patch_media_uploads(
            video_urns=[self.media_video.format("1")]
        )
        mock_response = self.generate_magic_mock(**{"status_code": 201})
        mock_response.headers = {"x-restli-id": "urn:li:ugcPost:1"}
        with patch_images as mock_images, patch_videos, (
            self.get_patch_exceptions_linkedin(mock_response)
        ) as mock_request:
            (
                _post_urn,
                published_urns,
            ) = self.SocialAccountLinkedin._linkedin_create_post(
                message="Hello", image_ids=[1], video_ids=[2]
            )
        mock_images.assert_not_called()
        self.assertEqual(published_urns, [])
        self.assertEqual(
            mock_request.call_args.kwargs["json_data"]["content"],
            {"media": {"id": self.media_video.format("1")}},
        )

    def test_linkedin_create_post_error(self):
        patch_images, patch_videos = self._patch_media_uploads()
        mock_response = self.generate_magic_mock(**{"status_code": 422})
        with patch_images, patch_videos, self.get_patch_exceptions_linkedin(
            mock_response
        ):
            with self.assertRaises(UserError) as context:
                self.SocialAccountLinkedin._linkedin_create_post(message="Hello")
        self.assertIn("could not be published on LinkedIn", str(context.exception))

    def test_linkedin_create_post_without_access_token(self):
        self.SocialAccountLinkedin.sudo().access_token = False
        self.assertEqual(
            self.SocialAccountLinkedin._linkedin_create_post(message="Hello"),
            (False, []),
        )

    def test_get_posts(self):
        mock_response = self.generate_magic_mock(
            **{
                "status_code": 200,
                "json_return_value": {
                    "elements": [
                        {"id": "123", "commentary": "Post 1"},
                        {"id": "456", "commentary": "Post 2"},
                    ]
                },
            }
        )

        patch_request_linkedin = self.get_patch_exceptions_linkedin(mock_response)

        with patch_request_linkedin as mock_request_linkedin:
            posts = self.SocialAccountLinkedin._get_posts()
            self.assertEqual(len(posts), 2)
            self.assertEqual(posts[0]["id"], "123")
            self.assertEqual(posts[1]["id"], "456")
            self.assertEqual(posts[0]["commentary"], "Post 1")
            self.assertEqual(posts[1]["commentary"], "Post 2")
            mock_request_linkedin.assert_called_once()
            call_kwargs = mock_request_linkedin.call_args.kwargs
            self.assertEqual(call_kwargs["endpoint"], "/posts")
            self.assertEqual(call_kwargs["params_values"]["q"], "author")
            self.assertEqual(
                call_kwargs["params_values"]["author"], "urn:li:organization:123456"
            )
            self.assertEqual(call_kwargs["headers"]["X-RestLi-Method"], "FINDER")

        mock_response_failed = self.generate_magic_mock(**{"status_code": 400})
        patch_request_linkedin_failed = self.get_patch_exceptions_linkedin(
            mock_response_failed
        )
        with patch_request_linkedin_failed as mock_request_linkedin_failed:
            with self.assertRaises(UserError):
                self.SocialAccountLinkedin._get_posts()
            mock_request_linkedin_failed.assert_called_once()

    def test_get_posts_by_ids(self):
        mock_response = self.generate_magic_mock(
            **{
                "status_code": 200,
                "json_return_value": {
                    "results": {
                        "urn:li:share:1": {
                            "id": "urn:li:share:1",
                            "commentary": "Post by id",
                            "content": {"media": {"id": "urn:li:image:1"}},
                            "author": "urn:li:organization:123456",
                            "publishedAt": 1735689600000,
                            "createdAt": 1735689600000,
                        }
                    },
                    "statuses": {},
                    "errors": {},
                },
            }
        )
        patch_request_linkedin = self.get_patch_exceptions_linkedin(mock_response)
        with patch_request_linkedin as mock_request_linkedin:
            posts = self.SocialAccountLinkedin._get_posts(
                params_fields=["ids"],
                params_values={"ids": ["urn:li:share:1"]},
            )
            self.assertEqual(len(posts), 1)
            self.assertEqual(posts[0]["id"], "urn:li:share:1")
            self.assertEqual(posts[0]["commentary"], "Post by id")
            self.assertEqual(posts[0]["content"], {"media": {"id": "urn:li:image:1"}})
            self.assertEqual(posts[0]["author"], "urn:li:organization:123456")
            mock_request_linkedin.assert_called_once()
            call_kwargs = mock_request_linkedin.call_args.kwargs
            self.assertEqual(call_kwargs["params_fields"], ["ids"])
            self.assertEqual(call_kwargs["params_values"], {"ids": ["urn:li:share:1"]})
            self.assertEqual(call_kwargs["headers"]["X-RestLi-Method"], "BATCH_GET")

    def test_get_posts_merges_the_author_params(self):
        """``add_values`` keeps the given params and adds the author finder."""
        mock_response = self.generate_magic_mock(
            **{"status_code": 200, "json_return_value": {"elements": []}}
        )
        with self.get_patch_exceptions_linkedin(mock_response) as mock_request_linkedin:
            self.SocialAccountLinkedin._get_posts(
                params_fields=["sortBy"],
                params_values={"sortBy": "LAST_MODIFIED"},
                add_values=True,
            )
        call_kwargs = mock_request_linkedin.call_args.kwargs
        self.assertEqual(
            call_kwargs["params_fields"], ["sortBy", "q", "author", "count"]
        )
        self.assertEqual(call_kwargs["params_values"]["sortBy"], "LAST_MODIFIED")
        self.assertEqual(call_kwargs["params_values"]["q"], "author")

    def test_get_all_posts_walks_every_page(self):
        """The feed is read until a page comes back empty."""
        pages = [
            [{"id": f"urn:li:share:{index}"} for index in range(3)],
            [{"id": "urn:li:share:3"}],
            [],
        ]
        with patch.object(
            type(self.SocialAccountLinkedin), "_get_posts", side_effect=pages
        ) as mock_get_posts:
            posts, complete = self.SocialAccountLinkedin._get_all_posts()
        self.assertTrue(complete)
        self.assertEqual(len(posts), 4)
        self.assertEqual(mock_get_posts.call_count, 3)
        starts = [
            call.kwargs["params_values"]["start"]
            for call in mock_get_posts.call_args_list
        ]
        self.assertEqual(starts, [0, 100, 200])

    def test_get_all_posts_keeps_reading_after_a_short_page(self):
        """A page shorter than asked is not the end of the feed."""
        pages = [[{"id": "urn:li:share:1"}], [{"id": "urn:li:share:2"}], []]
        with patch.object(
            type(self.SocialAccountLinkedin), "_get_posts", side_effect=pages
        ):
            posts, complete = self.SocialAccountLinkedin._get_all_posts()
        self.assertTrue(complete)
        self.assertEqual(
            [post["id"] for post in posts], ["urn:li:share:1", "urn:li:share:2"]
        )

    @mute_logger(LOGGER_ACCOUNT_LINKEDIN)
    def test_get_all_posts_stops_at_the_page_cap(self):
        """A feed longer than the cap is reported as read partially."""
        with patch.object(
            type(self.SocialAccountLinkedin),
            "_get_posts",
            return_value=[{"id": "urn:li:share:1"}],
        ) as mock_get_posts:
            posts, complete = self.SocialAccountLinkedin._get_all_posts()
        self.assertFalse(complete)
        self.assertEqual(mock_get_posts.call_count, _POSTS_MAX_PAGES_LINKEDIN)
        self.assertEqual(len(posts), 1)

    def test_get_linkedin_images_download_url(self):
        mock_response = self.generate_magic_mock(
            **{
                "status_code": 200,
                "json_return_value": {
                    "results": {
                        "urn:li:image:1": {"downloadUrl": "https://fake/1.png"},
                        "urn:li:image:2": {},
                    }
                },
            }
        )
        with self.get_patch_exceptions_linkedin(mock_response) as mock_request:
            urls = self.SocialAccountLinkedin._get_linkedin_images_download_url(
                ["urn:li:image:1", "urn:li:image:2"]
            )
        self.assertEqual(urls, {"urn:li:image:1": "https://fake/1.png"})
        self.assertEqual(
            mock_request.call_args.kwargs["headers"]["X-RestLi-Method"], "BATCH_GET"
        )

    @mute_logger(LOGGER_ACCOUNT_LINKEDIN)
    def test_get_linkedin_images_download_url_error_is_not_fatal(self):
        """A failure reading the images does not stop the statistics pass."""
        mock_response = self.generate_magic_mock(**{"status_code": 403})
        with self.get_patch_exceptions_linkedin(mock_response):
            urls = self.SocialAccountLinkedin._get_linkedin_images_download_url(
                ["urn:li:image:1"]
            )
        self.assertEqual(urls, {})
        self.assertEqual(
            self.SocialAccountLinkedin._get_linkedin_images_download_url([]), {}
        )

    def _generate_update_posts_statistics_patches(
        self, ugc_posts, feed_is_complete=True
    ):
        """Patches of a statistics pass.

        ``feed_is_complete`` is what the feed reader answers along the posts:
        the sweep of the publications gone from LinkedIn only runs when the
        whole feed was read.
        """
        return (
            self.generate_patch(
                **{
                    "model_patch": PATCH_ACCOUNT_LINKEDIN.format(
                        "validate_access_token"
                    ),
                    "return_value": True,
                }
            ),
            self.generate_patch(
                **{
                    "model_patch": PATCH_ACCOUNT_LINKEDIN.format("_get_posts"),
                    "return_value": ugc_posts,
                }
            ),
            self.generate_patch(
                **{
                    "model_patch": PATCH_ACCOUNT_LINKEDIN.format("_get_all_posts"),
                    "return_value": (ugc_posts, feed_is_complete),
                }
            ),
            self.generate_patch(
                **{
                    "model_patch": PATCH_ACCOUNT_LINKEDIN.format(
                        "_get_entity_statistics"
                    ),
                    "side_effect": lambda *args, **kwargs: {},
                }
            ),
            self.generate_patch(
                **{
                    "model_patch": PATCH_POST_ACCOUNT_LINKEDIN.format(
                        "_get_assets_save"
                    ),
                    "side_effect": lambda *args, **kwargs: None,
                }
            ),
            self.generate_patch(
                **{
                    "model_patch": PATCH_ACCOUNT_LINKEDIN.format(
                        "_linkedin_read_watched_figures"
                    ),
                    "return_value": dict(RECENT_STATISTICS_LINKEDIN),
                }
            ),
        )

    def test_update_posts_statistics_single_post_preserves_urns(self):
        ugc_posts = [
            {
                "id": "urn:li:share:new",
                "commentary": "Single post",
                "content": {"media": {"id": "urn:li:video:1"}},
                "publishedAt": 1735689600000,
                "author": "urn:li:organization:123456",
            }
        ]
        (
            patch_validate,
            patch_get_posts,
            patch_all_posts,
            patch_entity,
            patch_assets,
            patch_page,
        ) = self._generate_update_posts_statistics_patches(ugc_posts)
        self.SocialAccountLinkedin.linkedin_statistics_checkpoint = "untouched"
        with patch_validate, patch_get_posts as mock_get_posts, patch_all_posts, (
            patch_entity
        ), patch_assets, patch_page as mock_page:
            self.SocialAccountLinkedin._update_posts_statistics(
                "urn:li:share:new", None
            )
            mock_get_posts.assert_called_once()
            self.assertEqual(
                mock_get_posts.call_args.kwargs.get("params_fields"), ["ids"]
            )
            mock_page.assert_not_called()
        self.assertEqual(
            self.SocialAccountLinkedin.linkedin_statistics_checkpoint,
            "untouched",
            msg="Refreshing one publication says nothing about the page.",
        )
        self.assertEqual(self.SocialPostAccountLinkedin.remote_ref, "1234567890")
        post_account = self.SocialPostAccount.search(
            [("remote_ref", "=", "urn:li:share:new")]
        )
        self.assertTrue(post_account)
        self.assertEqual(post_account.message, "Single post")
        self.assertEqual(post_account.actor_urn, "urn:li:organization:123456")
        self.assertTrue(
            post_account.has_video,
            msg="A post whose media is a video URN is marked as a video post.",
        )

    def test_update_posts_statistics_single_post_keeps_the_account_totals(self):
        """Refreshing one post must not turn its figures into the totals."""
        account = self.SocialAccountLinkedin
        account.write(
            {
                "click_count": 5,
                "like_count": 17,
                "comment_count": 3,
                "share_count": 2,
                "engagement": 0.18,
                "impression_count": 346,
            }
        )
        ugc_posts = [
            {
                "id": "urn:li:share:new",
                "commentary": "Single post",
                "content": {},
                "publishedAt": 1735689600000,
                "author": "urn:li:organization:123456",
            }
        ]
        (
            patch_validate,
            patch_get_posts,
            patch_all_posts,
            __,
            patch_assets,
            patch_page,
        ) = self._generate_update_posts_statistics_patches(ugc_posts)
        patch_entity = self.generate_patch(
            **{
                "model_patch": PATCH_ACCOUNT_LINKEDIN.format("_get_entity_statistics"),
                "return_value": {"urn:li:share:new": (0, 1, 0, 0, 0, 0)},
            }
        )
        with patch_validate, patch_get_posts, patch_all_posts, patch_entity, (
            patch_assets
        ), patch_page:
            account._update_posts_statistics("urn:li:share:new", None)
        self.assertEqual(account.like_count, 17)
        self.assertEqual(account.impression_count, 346)
        self.assertEqual(account.engagement, 0.18)
        self.assertEqual(
            self.SocialPostAccount.search(
                [("remote_ref", "=", "urn:li:share:new")]
            ).like_count,
            1,
        )

    def test_update_posts_statistics_full_list_updates_the_account_totals(self):
        """The whole feed was read, so its sum is the total of the account."""
        account = self.SocialAccountLinkedin
        account.write({"like_count": 17, "impression_count": 346})
        ugc_posts = [
            {
                "id": "urn:li:share:new",
                "commentary": "Single post",
                "content": {},
                "publishedAt": 1735689600000,
                "author": "urn:li:organization:123456",
            }
        ]
        (
            patch_validate,
            patch_get_posts,
            patch_all_posts,
            __,
            patch_assets,
            patch_page,
        ) = self._generate_update_posts_statistics_patches(ugc_posts)
        patch_entity = self.generate_patch(
            **{
                "model_patch": PATCH_ACCOUNT_LINKEDIN.format("_get_entity_statistics"),
                "return_value": {"urn:li:share:new": (0, 1, 0, 0, 0, 12)},
            }
        )
        with patch_validate, patch_get_posts, patch_all_posts, patch_entity, (
            patch_assets
        ), patch_page:
            account._update_posts_statistics(False, None)
        self.assertEqual(account.like_count, 1)
        self.assertEqual(account.impression_count, 12)

    def test_update_posts_statistics_marks_the_page(self):
        """The import leaves the figures the check for updates compares with."""
        account = self.SocialAccountLinkedin
        account.write(
            {
                "linkedin_statistics_checkpoint": "stale",
                "need_update": True,
            }
        )
        ugc_posts = [
            {
                "id": "urn:li:share:new",
                "commentary": "Single post",
                "content": {},
                "publishedAt": 1735689600000,
                "author": "urn:li:organization:123456",
            }
        ]
        (
            patch_validate,
            patch_get_posts,
            patch_all_posts,
            patch_entity,
            patch_assets,
            patch_page,
        ) = self._generate_update_posts_statistics_patches(ugc_posts)
        with patch_validate, patch_get_posts, patch_all_posts, patch_entity, (
            patch_assets
        ), patch_page:
            account._update_posts_statistics(False, None)
        self.assertEqual(
            account.linkedin_statistics_checkpoint,
            account._linkedin_statistics_checkpoint(RECENT_STATISTICS_LINKEDIN),
        )
        self.assertFalse(account.need_update)

    def test_full_resync_cleans_stale_urns(self):
        """A publication gone from a feed read whole is marked as deleted."""
        remote_ref = self.SocialPostAccountLinkedin.remote_ref
        ugc_posts = [
            {
                "id": "urn:li:share:other",
                "commentary": "Other post",
                "content": {},
                "publishedAt": 1735689600000,
                "author": "urn:li:organization:123456",
            }
        ]
        (
            patch_validate,
            patch_get_posts,
            patch_all_posts,
            patch_entity,
            patch_assets,
            patch_page,
        ) = self._generate_update_posts_statistics_patches(ugc_posts)
        with patch_validate, patch_get_posts, patch_all_posts, patch_entity, (
            patch_assets
        ), patch_page:
            self.SocialAccountLinkedin._full_resync()
        self.assertFalse(self.SocialPostAccountLinkedin.post_account_url)
        self.assertEqual(self.SocialPostAccountLinkedin.state, "deleted")
        self.assertEqual(self.SocialPostAccountLinkedin.remote_ref, remote_ref)

    def test_full_resync_reads_each_account_once(self):
        """The accounts left to the base must not come back as every account.

        The connector reconciles its own accounts and delegates the rest,
        none here, and the ordinary refresh takes an empty recordset as
        every account: without the guard of the base each account was read
        twice, once whole and once more in the ordinary way.
        """
        with self.generate_patch(
            model_patch=PATCH_ACCOUNT_LINKEDIN.format("_refresh_linkedin_posts"),
            return_value=True,
        ) as mock_refresh:
            self.SocialAccountLinkedin._full_resync()
        mock_refresh.assert_called_once_with(self.SocialAccountLinkedin, full_feed=True)

    def test_update_posts_statistics_keeps_a_publication_off_the_page(self):
        """Update no longer walks the feed, so it cannot conclude a deletion.

        The publication missing from the page of recently modified ones is not
        gone: nothing was read that could say so. Only the full resync decides
        that, which is what ``test_full_resync_cleans_stale_urns`` covers.
        """
        ugc_posts = [
            {
                "id": "urn:li:share:other",
                "commentary": "Other post",
                "content": {},
                "publishedAt": 1735689600000,
                "author": "urn:li:organization:123456",
            }
        ]
        (
            patch_validate,
            patch_get_posts,
            patch_all_posts,
            patch_entity,
            patch_assets,
            patch_page,
        ) = self._generate_update_posts_statistics_patches(ugc_posts)
        with patch_validate, patch_get_posts as mock_get_posts, (
            patch_all_posts
        ) as mock_all_posts, patch_entity, patch_assets, patch_page:
            self.SocialAccountLinkedin._update_posts_statistics(False, None)
        self.assertEqual(self.SocialPostAccountLinkedin.state, "posted")
        mock_all_posts.assert_not_called()
        mock_get_posts.assert_called_once()
        self.assertEqual(
            mock_get_posts.call_args.kwargs.get("params_values", {}).get("sortBy"),
            "LAST_MODIFIED",
            msg="The page has to be the one of the recently modified posts.",
        )

    def test_update_posts_statistics_refreshes_a_publication_off_the_page(self):
        """The figures of a stored publication are refreshed without the feed.

        It is the whole point of the change: the statistics are asked for by
        URN, and Odoo already knows the URNs of the account, so a publication
        the discovery page did not bring still gets its figures.
        """
        post_account = self.SocialPostAccountLinkedin
        post_account.write({"like_count": 0, "impression_count": 0})
        ugc_posts = [
            {
                "id": "urn:li:share:other",
                "commentary": "Other post",
                "content": {},
                "publishedAt": 1735689600000,
                "author": "urn:li:organization:123456",
            }
        ]
        (
            patch_validate,
            patch_get_posts,
            patch_all_posts,
            __,
            patch_assets,
            patch_page,
        ) = self._generate_update_posts_statistics_patches(ugc_posts)
        statistics = {post_account.remote_ref: (1, 7, 2, 0, 0.5, 42)}
        patch_entity = patch(
            PATCH_ACCOUNT_LINKEDIN.format("_get_entity_statistics"),
            autospec=True,
            return_value=statistics,
        )
        with patch_validate, patch_get_posts, patch_all_posts, (
            patch_entity
        ) as mock_entity, patch_assets, patch_page:
            self.SocialAccountLinkedin._update_posts_statistics(False, None)
        asked = [post["id"] for post in mock_entity.call_args.kwargs.get("posts") or []]
        self.assertIn(
            post_account.remote_ref,
            asked,
            msg="The stored URNs are asked about even when the page misses them.",
        )
        self.assertEqual(post_account.like_count, 7)
        self.assertEqual(post_account.impression_count, 42)
        self.assertEqual(
            post_account.state,
            "posted",
            msg="Refreshing the figures must not touch the state.",
        )

    def test_update_posts_statistics_partial_feed_keeps_the_publications(self):
        """A feed read partially says nothing about what is missing from it."""
        ugc_posts = [
            {
                "id": "urn:li:share:other",
                "commentary": "Other post",
                "content": {},
                "publishedAt": 1735689600000,
                "author": "urn:li:organization:123456",
            }
        ]
        (
            patch_validate,
            patch_get_posts,
            patch_all_posts,
            patch_entity,
            patch_assets,
            patch_page,
        ) = self._generate_update_posts_statistics_patches(
            ugc_posts, feed_is_complete=False
        )
        with patch_validate, patch_get_posts, patch_all_posts, patch_entity, (
            patch_assets
        ), patch_page:
            self.SocialAccountLinkedin._update_posts_statistics(False, None)
        self.assertEqual(self.SocialPostAccountLinkedin.state, "posted")
        self.assertEqual(self.SocialPostAccountLinkedin.remote_ref, "1234567890")

    def test_update_posts_statistics_restores_a_publication_back_online(self):
        """A line wrongly marked is recognised again by its remote reference."""
        post_account = self.SocialPostAccountLinkedin
        post_account.write({"state": "deleted", "post_account_url": False})
        ugc_posts = [
            {
                "id": post_account.remote_ref,
                "commentary": "Back online",
                "content": {},
                "publishedAt": 1735689600000,
                "author": "urn:li:organization:123456",
            }
        ]
        (
            patch_validate,
            patch_get_posts,
            patch_all_posts,
            patch_entity,
            patch_assets,
            patch_page,
        ) = self._generate_update_posts_statistics_patches(ugc_posts)
        with patch_validate, patch_get_posts, patch_all_posts, patch_entity, (
            patch_assets
        ), patch_page:
            self.SocialAccountLinkedin._update_posts_statistics(False, None)
        self.assertEqual(post_account.state, "posted")
        self.assertTrue(post_account.post_account_url)

    def _patch_daily_statistics(self, elements):
        """Patch the finder answering one bucket per day."""
        return (
            self.generate_patch(
                **{
                    "type_object": True,
                    "model_patch": self.SocialAccountLinkedin,
                    "method_patch": "_get_default_filter_date",
                    "return_value": (
                        "2025-01-01T00:00:00",
                        "2025-01-07T23:59:59",
                    ),
                }
            ),
            self.generate_patch(
                **{
                    "type_object": True,
                    "model_patch": self.SocialAccountLinkedin,
                    "method_patch": "_request_linkedin",
                    "return_value": self.generate_magic_mock(
                        **{
                            "status_code": 200,
                            "json_return_value": {"elements": elements},
                        }
                    ),
                }
            ),
        )

    def _daily_bucket(self, start, **statistics):
        return {
            "timeRange": {"start": start, "end": start + 86400000},
            "totalShareStatistics": statistics,
        }

    def test_get_linkedin_daily_statistics_keys_the_buckets_by_day(self):
        """Every bucket is keyed by the ISO day of its ``timeRange.start``."""
        _patch_dates, patch_request = self._patch_daily_statistics(
            [
                self._daily_bucket(1735776000000, impressionCount=100),
                self._daily_bucket(1736035200000, impressionCount=180),
            ]
        )
        with patch_request:
            statistics = self.SocialAccountLinkedin._get_linkedin_daily_statistics(
                0, 0, "DAY"
            )
        self.assertEqual(sorted(statistics), ["2025-01-02", "2025-01-05"])
        self.assertEqual(statistics["2025-01-02"][5], 100)
        self.assertEqual(statistics["2025-01-05"][5], 180)

    def test_get_linkedin_daily_statistics_adds_up_the_same_day(self):
        """Two buckets of one day are added up, not overwritten."""
        _patch_dates, patch_request = self._patch_daily_statistics(
            [
                # Both are hours of the 2nd of january, so both are that day.
                self._daily_bucket(1735776000000, impressionCount=100),
                self._daily_bucket(1735776000000 + 3600000, impressionCount=180),
            ]
        )
        with patch_request:
            statistics = self.SocialAccountLinkedin._get_linkedin_daily_statistics(
                0, 0, "DAY"
            )
        self.assertEqual(list(statistics), ["2025-01-02"])
        self.assertEqual(statistics["2025-01-02"][5], 280)

    # --- The time series ------------------------------------------------

    def _patch_reader(self, buckets=None, side_effect=None):
        """Answer the daily finder without reaching LinkedIn."""
        return patch(
            PATCH_ACCOUNT_LINKEDIN.format("_get_linkedin_daily_statistics"),
            autospec=True,
            **(
                {"side_effect": side_effect}
                if side_effect
                else {"return_value": dict(buckets or {})}
            ),
        )

    def _statistics_of(self, account):
        return self.env["social.account.statistics"].search(
            [("account_id", "=", account.id)]
        )

    def test_snapshot_statistics_writes_one_row_per_bucket(self):
        """Every bucket LinkedIn answers becomes a row, and only those."""
        with self._patch_reader(
            {
                "2025-01-01": (1, 2, 3, 4, 0.5, 100),
                "2025-01-02": (5, 6, 7, 8, 0.25, 200),
            }
        ):
            self.SocialAccountLinkedin._snapshot_statistics(
                date(2025, 1, 1), date(2025, 1, 7)
            )
        rows = self._statistics_of(self.SocialAccountLinkedin)
        self.assertEqual(len(rows), 2, msg="A day with no bucket leaves no row.")
        row = rows.filtered(lambda row: row.date == date(2025, 1, 1))
        self.assertEqual(
            (
                row.click_count,
                row.like_count,
                row.comment_count,
                row.share_count,
                row.impression_count,
            ),
            (1, 2, 3, 4, 100),
        )
        self.assertAlmostEqual(row.engagement, 0.5)

    def test_snapshot_statistics_asks_for_the_day_after_the_range(self):
        """LinkedIn takes the end of an interval as exclusive."""
        with self._patch_reader() as mock_reader:
            self.SocialAccountLinkedin._snapshot_statistics(
                date(2025, 1, 1), date(2025, 1, 7)
            )
        start_time, end_time, granularity = mock_reader.call_args.args[1:]
        self.assertEqual(granularity, "DAY")
        self.assertEqual(
            round((end_time - start_time) / (24 * 3600 * 1000)),
            7,
            msg="Asking up to the last day itself would leave its bucket out.",
        )

    def test_snapshot_statistics_skips_an_account_without_organization(self):
        """The finder is asked for an organization, so there is nothing to ask."""
        self.SocialAccountLinkedin.remote_ref = False
        with self._patch_reader({"2025-01-01": (0, 0, 0, 0, 0.0, 1)}) as mock_reader:
            self.SocialAccountLinkedin._snapshot_statistics(
                date(2025, 1, 1), date(2025, 1, 1)
            )
        mock_reader.assert_not_called()
        self.assertFalse(self._statistics_of(self.SocialAccountLinkedin))

    def test_snapshot_statistics_isolates_a_failing_account(self):
        """A 403 on one account keeps the rows of the ones already written."""
        other = self.SocialAccount.create(
            {
                "name": "Second organization",
                "media_id": self.media_linkedin_id.id,
                "remote_ref": "urn:li:organization:654321",
            }
        )

        def refuse_the_second(account, start_time, end_time, granularity):
            if account.linkedin_account_id == "654321":
                raise UserError(_("403 forbidden"))
            return {"2025-01-01": (0, 0, 0, 0, 0.0, 10)}

        with self._patch_reader(side_effect=refuse_the_second), mute_logger(
            "odoo.addons.social_media_linkedin.models.social_account"
        ):
            (self.SocialAccountLinkedin | other)._snapshot_statistics(
                date(2025, 1, 1), date(2025, 1, 1)
            )
        self.assertEqual(len(self._statistics_of(self.SocialAccountLinkedin)), 1)
        self.assertFalse(self._statistics_of(other))

    def test_snapshot_statistics_with_a_range_of_no_days(self):
        with self._patch_reader() as mock_reader:
            self.SocialAccountLinkedin._snapshot_statistics(
                date(2025, 1, 7), date(2025, 1, 1)
            )
            self.SocialAccountLinkedin._snapshot_statistics(None, None)
        mock_reader.assert_not_called()

    def test_snapshot_statistics_leaves_the_other_media_to_their_connector(self):
        with self._patch_reader() as mock_reader:
            self.social_account_id._snapshot_statistics(
                date(2025, 1, 1), date(2025, 1, 1)
            )
        mock_reader.assert_not_called()

    def test_the_backfill_asks_for_the_whole_history(self):
        """The first import reaches as far back as LinkedIn may answer."""
        start, end = self.SocialAccountLinkedin._linkedin_backfill_window()
        self.assertEqual(end, fields.Date.today())
        self.assertEqual(
            start,
            end - relativedelta(months=_STATISTICS_HISTORY_MONTHS_LINKEDIN),
        )
        with patch(
            PATCH_ACCOUNT_LINKEDIN.format("_snapshot_statistics"), autospec=True
        ) as mock_snapshot:
            self.SocialAccountLinkedin._backfill_statistics()
        self.assertEqual(mock_snapshot.call_args.args[1:], (start, end))

    def test_the_refresh_asks_for_the_rewrite_window(self):
        """LinkedIn revises days already past, so the last ones are asked again."""
        start, end = self.SocialAccountLinkedin._linkedin_refresh_window()
        self.assertEqual(end, fields.Date.today())
        self.assertEqual((end - start).days, _UPDATE_CHECK_DAYS_LINKEDIN)
        with patch(
            PATCH_ACCOUNT_LINKEDIN.format("_snapshot_linkedin_statistics"),
            autospec=True,
            return_value={},
        ) as mock_snapshot:
            self.assertTrue(self.SocialAccountLinkedin._refresh_statistics())
        self.assertEqual(mock_snapshot.call_args.args[1:], (start, end))

    def test_action_refresh_statistics_writes_the_rows(self):
        """The button of the account form goes through the very same path."""
        today = fields.Date.today()
        Bus = self.env["bus.bus"]
        with self._patch_reader(
            {today.isoformat(): (0, 0, 0, 0, 0.0, 42)}
        ), patch.object(type(Bus), "_sendone", autospec=True) as mock_sendone:
            self.SocialAccountLinkedin.action_refresh_statistics()
        rows = self._statistics_of(self.SocialAccountLinkedin)
        self.assertEqual(rows.impression_count, 42)
        self.assertEqual(mock_sendone.call_args[0][2], "social_form_success")

    def test_the_cron_writes_the_series_of_a_flagged_account(self):
        """``need_update`` says an import is pending, not that nothing moved."""
        self._isolate_linkedin_account()
        self._mark_the_page_as_imported()
        self.SocialAccountLinkedin.write(
            {"pending_initial_sync": False, "need_update": True}
        )
        with self._patch_recent_statistics():
            self.SocialAccount._run_check_media_updates()
        self.assertEqual(
            len(self._statistics_of(self.SocialAccountLinkedin)),
            len(RECENT_STATISTICS_LINKEDIN),
            msg="A flagged account must not be starved of its time series.",
        )

    def test_the_initial_sync_backfills_the_account(self):
        self._isolate_linkedin_account()
        self.SocialAccountLinkedin.write({"pending_initial_sync": True})
        with self._patch_reader(
            {"2025-01-01": (0, 0, 0, 0, 0.0, 3)}
        ) as mock_reader, patch(
            PATCH_ACCOUNT_LINKEDIN.format("_refresh_linkedin_posts"), autospec=True
        ):
            self.SocialAccount._run_initial_sync()
        mock_reader.assert_called_once()
        self.assertEqual(len(self._statistics_of(self.SocialAccountLinkedin)), 1)
        self.assertFalse(self.SocialAccountLinkedin.pending_initial_sync)

    def test_a_failing_backfill_keeps_the_posts_already_imported(self):
        """The history costs its own calls, so it gets its own savepoint."""
        self._isolate_linkedin_account()
        self.SocialAccountLinkedin.write({"pending_initial_sync": True})
        with self._patch_reader(side_effect=UserError(_("history unavailable"))), patch(
            PATCH_ACCOUNT_LINKEDIN.format("_refresh_linkedin_posts"), autospec=True
        ) as mock_refresh, mute_logger(
            "odoo.addons.social_media_linkedin.models.social_account"
        ):
            self.SocialAccount._run_initial_sync()
        mock_refresh.assert_called_once()
        self.assertFalse(self.SocialAccountLinkedin.pending_initial_sync)
        self.assertFalse(self._statistics_of(self.SocialAccountLinkedin))

    @patch(PATCH_ACCOUNT_LINKEDIN.format("_request_linkedin"))
    def test_validate_linkedin_access_token(self, mock_request_linkedin):
        mock_request_linkedin.return_value = {"active": True}
        result = self.SocialAccountLinkedin._validate_linkedin_access_token("token")
        self.assertTrue(result)

        mock_request_linkedin.return_value = {"active": False}
        result = self.SocialAccountLinkedin._validate_linkedin_access_token("token")
        self.assertFalse(result)

        self.assertEqual(mock_request_linkedin.call_count, 2)

    @patch(PATCH_ACCOUNT_LINKEDIN.format("_request_linkedin"))
    def test_validate_linkedin_access_token_stores_the_scopes(
        self, mock_request_linkedin
    ):
        """The introspection is the only place LinkedIn says what was granted."""
        account = self.SocialAccountLinkedin
        mock_request_linkedin.return_value = {
            "active": True,
            "scope": "w_member_social,r_organization_social",
        }
        self.assertTrue(account._validate_linkedin_access_token("token"))
        self.assertEqual(
            account.linkedin_granted_scopes,
            "r_organization_social, w_member_social",
        )

    @patch(PATCH_ACCOUNT_LINKEDIN.format("_request_linkedin"))
    def test_validate_linkedin_access_token_without_scopes(self, mock_request_linkedin):
        """An answer without scopes does not erase what is known."""
        account = self.SocialAccountLinkedin
        account.linkedin_granted_scopes = "r_ads"
        mock_request_linkedin.return_value = {"active": True}
        self.assertTrue(account._validate_linkedin_access_token("token"))
        self.assertEqual(account.linkedin_granted_scopes, "r_ads")

    def test_has_linkedin_scope(self):
        account = self.SocialAccountLinkedin
        account.linkedin_granted_scopes = "r_ads, w_member_social"
        self.assertTrue(account._has_linkedin_scope("r_ads"))
        self.assertFalse(account._has_linkedin_scope("r_ads_reporting"))

    def test_has_linkedin_scope_unknown(self):
        """Unknown scopes must not block an account that works."""
        account = self.SocialAccountLinkedin
        account.linkedin_granted_scopes = False
        self.assertTrue(account._has_linkedin_scope("r_ads"))

    def test_check_linkedin_scopes(self):
        account = self.SocialAccountLinkedin
        account.linkedin_granted_scopes = "r_ads"
        self.assertIsNone(account._check_linkedin_scopes(["r_ads"]))
        with self.assertRaises(UserError) as error:
            account._check_linkedin_scopes(["r_ads", "r_ads_reporting"])
        self.assertIn("r_ads_reporting", str(error.exception))

    def test_get_default_filter_date(self):
        start_date = datetime.now()
        end_date = start_date + timedelta(days=30)
        self.assertEqual(
            self.SocialAccountLinkedinData._get_default_filter_date(
                start_date=start_date, end_date=end_date
            ),
            (start_date, end_date),
        )

    @patch("odoo.addons.social_media_linkedin.models.social_account.requests.request")
    def test_request_linkedin(self, mock_request):
        url_test = "https://api-fake.linkedin.com/v2/test"
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.url = url_test
        mock_request.return_value = mock_response

        result = self.SocialAccount._request_linkedin(
            complete_url=url_test,
            return_json=True,
            params_fields=["authors"],
            params_values={
                "q": "authors",
                "authors": ["urn:li:organization:123456789"],
            },
        )
        self.assertEqual(result, mock_response.json())

        mock_request._URL_V2_LINKEDIN = "https://api-fake.linkedin.com"
        result = self.SocialAccount._request_linkedin(
            linkedin_v2=True,
            return_json=True,
            endpoint="/test",
            params_fields=["authors"],
            params_values={
                "q": "authors",
                "authors": ["urn:li:organization:123456789"],
            },
        )
        self.assertEqual(result, mock_response.json())

        mock_request._URL_REST_LINKEDIN = "https://api-rest-fake.linkedin.com"
        result = self.SocialAccount._request_linkedin(
            token="fake-token",
            return_json=True,
            endpoint="/test-api-rest",
            params_fields=["authors"],
            params_values={
                "q": "authors",
                "authors": ["urn:li:organization:123456789"],
            },
        )
        self.assertEqual(result, mock_response.json())

        self.assertEqual(mock_request.call_count, 3)

    def test_unique_account(self):
        with self.assertRaises(UserError):
            self.SocialAccount._unique_account(
                linkedin_client_id="fake-client-id", linkedin_secret="fake-secret"
            )

    def test_update_account(self):
        res = self.SocialAccountLinkedin.action_update_account()
        self.assertEqual(res["context"]["default_linkedin_client"], "fake-client-id")

    def test_refresh_token(self):
        fake_response = {
            "access_token": "fake-access-token",
            "refresh_token": "fake-refresh-token",
            "expires_in": 3600,
        }
        with self._mock_linkedin(
            return_value=fake_response, account=self.SocialAccountLinkedin
        ) as mock_request:
            res = self.SocialAccountLinkedin._refresh_token()
            self.assertEqual(res, fake_response)
            mock_request.assert_called_once()

        mock_response = MagicMock()
        mock_response.text.return_value = "Error"
        with self._mock_linkedin(
            return_value=mock_response, account=self.SocialAccountLinkedin
        ) as mock_request:
            with self.assertRaises(UserError):
                self.SocialAccountLinkedin._refresh_token()

            mock_request.assert_called_once()

    @patch(PATCH_ACCOUNT_LINKEDIN.format("_request_linkedin"))
    def test_get_access_token_linkedin(self, mock_request_linkedin):
        mock_request_linkedin.return_value = "fake-csrf-token"
        result = self.SocialAccountLinkedin._get_access_token_linkedin(
            "CODE", "/web", {"state": "fake-csrf-token"}
        )
        self.assertEqual(result[2], "fake-csrf-token")

    def test_get_account_linkedin(self):
        organization_request_linkedin = {
            "elements": [{"organization": "organization:123456789"}]
        }
        organization_logo_mock = MagicMock()
        organization_logo_mock.status_code = 200
        organization_logo_mock.content = b"fake image data"
        organization_name = "Organization Test"
        organization_id = "organization123456789"
        response_organization = {
            "id": organization_id,
            "vanityName": organization_name,
            "name": {"localized": {"es_ES": organization_name}},
            "logoV2": {
                "original~": {
                    "elements": [
                        {
                            "artifact": "logo_400_400/image_organization123456789",
                            "identifiers": [
                                {
                                    "identifier": "https://www.medias.com/logo_400_400/image_organization123456789"
                                }
                            ],
                        }
                    ]
                }
            },
        }
        patch_request_linkedin = self.get_patch_exceptions_linkedin(
            side_effect=[
                organization_request_linkedin,
                response_organization,
                organization_logo_mock,
            ]
        )
        with patch_request_linkedin as mock_request:
            res = self.SocialAccount._get_account_linkedin("fake-access-token")
            self.assertEqual(res[0]["id"], organization_id)
            self.assertEqual(res[0]["localizedName"], organization_name)
            self.assertEqual(res[0]["vanityName"], organization_name)
            self.assertTrue(res[0]["logo"])
            self.assertEqual(mock_request.call_count, 3)

    def test_get_account_linkedin_reports_the_error_of_linkedin(self):
        """The failure used to be hidden behind an Expected singleton."""
        account = self.SocialAccountLinkedin
        account.write({"linkedin_account_id": "123456"})
        error_response = MagicMock(status_code=403)
        error_response.text = '{"message": "Not enough permissions"}'
        with patch.object(
            type(self.SocialAccount),
            "_request_linkedin",
            return_value=error_response,
        ), self.assertRaises(UserError) as error:
            account._get_account_linkedin("fake-access-token")
        self.assertIn("Not enough permissions", str(error.exception))

    def test_get_account_linkedin_keeps_the_organizations_that_answered(self):
        """One unreadable organization must not drop the others."""
        account = self.SocialAccountLinkedin
        account.sudo().write({"remote_ref": "urn:li:organization:123456"})
        error_response = MagicMock(status_code=403)
        error_response.text = '{"message": "Not enough permissions"}'
        messages = len(account.message_ids)
        patch_request_linkedin = self.get_patch_exceptions_linkedin(
            side_effect=[
                {
                    "elements": [
                        {"organization": "urn:li:organization:123456"},
                        {"organization": "urn:li:organization:999"},
                    ]
                },
                error_response,
                {
                    "id": "999",
                    "vanityName": "Readable",
                    "name": {"localized": {"en_US": "Readable"}},
                },
            ]
        )
        with patch_request_linkedin:
            res = self.SocialAccount._get_account_linkedin("fake-access-token")
        self.assertEqual([organization["id"] for organization in res], ["999"])
        self.assertEqual(len(account.message_ids), messages + 1)
        self.assertIn("Not enough permissions", account.message_ids[0].body)

    def test_get_account_linkedin_without_localized_name(self):
        """An organization without a localized name must not break the flow."""
        patch_request_linkedin = self.get_patch_exceptions_linkedin(
            side_effect=[
                {"elements": [{"organization": "urn:li:organization:123456"}]},
                {
                    "id": "123456",
                    "vanityName": "No name",
                    "name": {"localized": {}},
                },
            ]
        )
        with patch_request_linkedin:
            res = self.SocialAccount._get_account_linkedin("fake-access-token")
        self.assertEqual(len(res), 1)
        self.assertFalse(res[0]["localizedName"])

    def test_get_account_linkedin_prefers_the_language_of_the_user(self):
        """The name of the organization follows the language of the user."""
        patch_request_linkedin = self.get_patch_exceptions_linkedin(
            side_effect=[
                {"elements": [{"organization": "urn:li:organization:123456"}]},
                {
                    "id": "123456",
                    "vanityName": "Binhex",
                    "name": {
                        "localized": {"es_ES": "Nombre", "en_US": "Name"},
                    },
                },
            ]
        )
        self.env.user.lang = "en_US"
        with patch_request_linkedin:
            res = self.SocialAccount._get_account_linkedin("fake-access-token")
        self.assertEqual(res[0]["localizedName"], "Name")

    def test_get_account_linkedin_logo_without_preferred_size(self):
        organization_logo_mock = MagicMock()
        organization_logo_mock.status_code = 200
        organization_logo_mock.content = b"fake image data"
        response_organization = {
            "id": "organization123456789",
            "vanityName": "Organization Test",
            "name": {"localized": {"es_ES": "Organization Test"}},
            "logoV2": {
                "original~": {
                    "elements": [
                        {
                            "artifact": "logo_200_200/image_organization123456789",
                            "identifiers": [
                                {"identifier": "https://www.medias.com/logo_200_200"}
                            ],
                        }
                    ]
                }
            },
        }
        patch_request_linkedin = self.get_patch_exceptions_linkedin(
            side_effect=[
                {"elements": [{"organization": "organization:123456789"}]},
                response_organization,
                organization_logo_mock,
            ]
        )
        with patch_request_linkedin:
            res = self.SocialAccount._get_account_linkedin("fake-access-token")
        self.assertTrue(
            res[0]["logo"],
            msg="The first element is used when no 400x400 variant exists.",
        )

    def test_get_url_redirect(self):
        with patch(
            "odoo.models.BaseModel.get_base_url",
            autospec=True,
            return_value=self.url_callback,
        ) as base_url:
            result = self.wizard_account_id._get_url_redirect()
            self.assertEqual(result, self.url_callback)
            base_url.assert_called_once()

        with patch(
            PATCH_WIZARD_ACCOUNT.format("_get_url_redirect"), autospec=True
        ) as redirect_super:
            self.WizardAccount._get_url_redirect()
            redirect_super.assert_called_once()

    def test_generate_code(self):
        result = self.wizard_account_id._generate_code()
        self.assertEqual(len(result), 10)

    def test_action_add_account(self):
        with patch.object(
            type(self.wizard_account_id),
            "_get_url_redirect",
            return_value=self.url_callback,
        ), patch.object(
            type(self.wizard_account_id),
            "_generate_code",
            return_value="fake-code-token",
        ):
            result = self.wizard_account_id._action_add_account()
            self.assertIn("fake-client-id", result["url"])
            self.assertEqual(result["type"], "ir.actions.act_url")

            result = self.wizard_account_id.with_context(
                only_url=True
            )._action_add_account()
            self.assertIn("fake-client-id", result)

    def test_action_add_account_asks_for_the_module_scopes(self):
        """Without an account there is nothing but the defaults to ask for."""
        with patch.object(
            type(self.wizard_account_id),
            "_get_url_redirect",
            return_value=self.url_callback,
        ):
            url = self.wizard_account_id.with_context(
                only_url=True
            )._action_add_account()
        media = self.env.ref("social_media_linkedin.social_media_linkedin")
        for scope in media._get_linkedin_scopes():
            self.assertIn(scope, url)

    def test_action_add_account_asks_for_the_account_scopes(self):
        """Re-authorizing asks for the module scopes and the account edits."""
        account = self.SocialAccountLinkedin
        account.sudo().linkedin_granted_scopes = "r_basicprofile, r_fake_product"
        wizard = self.wizard_account_id.copy(
            {"account_id": account.id, "update_keys": True}
        )
        with patch.object(
            type(wizard), "_get_url_redirect", return_value=self.url_callback
        ):
            url = wizard.with_context(only_url=True)._action_add_account()
        self.assertIn("r_fake_product", url)
        for scope in account.media_id._get_linkedin_scopes():
            self.assertIn(scope, url)

    def test_get_linkedin_authorization_scopes_without_them(self):
        """An account that knows no scopes falls back to the defaults."""
        account = self.SocialAccountLinkedin
        account.sudo().linkedin_granted_scopes = False
        self.assertEqual(
            account._get_linkedin_authorization_scopes(),
            account.media_id._get_linkedin_scopes(),
        )

    def test_get_linkedin_authorization_scopes_keeps_the_module_ones(self):
        """A token granted before a module was installed still asks for it."""
        account = self.SocialAccountLinkedin
        account.sudo().linkedin_granted_scopes = "w_member_social"
        scopes = account._get_linkedin_authorization_scopes()
        for scope in account.media_id._get_linkedin_scopes():
            self.assertIn(scope, scopes)
        self.assertEqual(len(scopes), len(set(scopes)))

    def test_action_valid_add_account(self):
        with patch.object(type(self.SocialAccount), "_unique_account") as uni_acc:
            self.wizard_account_id._action_valid_add_account()
            uni_acc.assert_called_once()

    def test_update_account_keys(self):
        with patch.object(
            type(self.wizard_account_id),
            "_update_account",
        ) as upd_acc:
            self.wizard_account_id._update_account()
            upd_acc.assert_called_once()

        self.wizard_account_id.write(
            {
                "update_keys": True,
                "account_id": self.SocialAccountLinkedin.id,
                "linkedin_client": "new-client-id",
                "linkedin_secret": "new-secret",
            }
        )
        result = self.wizard_account_id._update_account()
        self.assertEqual(result["type"], "ir.actions.act_url")
        self.assertEqual(result["target"], "self")
        account_sudo = self.SocialAccountLinkedin.sudo()
        self.assertEqual(account_sudo.linkedin_client_id, "fake-client-id")
        self.assertEqual(account_sudo.linkedin_secret, "fake-secret")

    def test_update_account_keys_rejects_the_keys_of_another_account(self):
        other = self.SocialAccount.sudo().create(
            {
                "name": "Another Linkedin",
                "media_id": self.media_linkedin_id.id,
                "linkedin_client_id": "taken-client-id",
                "linkedin_secret": "taken-secret",
            }
        )
        self.wizard_account_id.write(
            {
                "update_keys": True,
                "account_id": self.SocialAccountLinkedin.id,
                "linkedin_client": other.linkedin_client_id,
                "linkedin_secret": other.linkedin_secret,
            }
        )
        with self.assertRaises(UserError):
            self.wizard_account_id._update_account()

    @patch(PATCH_SOCIAL_BASE_MIXIN.format("_notify_user_client"))
    @patch(PATCH_ACCOUNT_LINKEDIN.format("_refresh_token"))
    def test_update_account_token(self, mock_refresh_linkedin, mock_notify_user):
        self.wizard_account_id.write(
            {
                "update_keys": False,
                "update_token": True,
                "account_id": self.SocialAccountLinkedin.id,
            }
        )
        mock_refresh_linkedin.return_value = {
            "access_token": "fake-access-token",
            "refresh_token": "fake-refresh-token",
            "expires_in": 1597560000,
        }
        self.wizard_account_id._update_account()
        mock_notify_user.assert_called_once()
        self.assertEqual(self.SocialAccountLinkedin.access_token, "fake-access-token")
        self.assertEqual(
            self.SocialAccountLinkedin.refresh_access_token, "fake-refresh-token"
        )

    @patch(PATCH_ACCOUNT_LINKEDIN.format("_get_account_linkedin"))
    def test_update_account_organization(self, mock_linkedin):
        self.wizard_account_id.write(
            {
                "account_id": self.SocialAccountLinkedin.id,
            }
        )
        mock_linkedin.return_value = [
            {
                "localizedName": "Localized X",
                "vanityName": "Vanity X",
                "logo": self.VALID_PNG_B64,
            }
        ]
        self.wizard_account_id._update_account()
        self.assertEqual(self.SocialAccountLinkedin.name, "Localized X")
        self.assertEqual(self.SocialAccountLinkedin.username, "Vanity X")
        mock_linkedin.assert_called_once()

    def test_get_csrf_state_token(self):
        fake_code_hmac = "fake-hmac-code"
        with patch.object(
            type(self.wizard_account_id), "_generate_code", autospec=True
        ) as mock_fake_code, patch(
            PATCH_WIZARD_ACCOUNT_LINKEDIN.format("hmac"),
            autospec=True,
            return_value=fake_code_hmac,
        ) as mock_hmac:
            result = self.wizard_account_id._get_csrf_state_token()
            self.assertEqual(result, fake_code_hmac)
            mock_hmac.assert_called_once()
            mock_fake_code.assert_called_once()

        with patch(
            PATCH_WIZARD_ACCOUNT.format("_get_csrf_state_token"), autospec=True
        ) as mock_hmac_super:
            self.WizardAccount._get_csrf_state_token()
            mock_hmac_super.assert_called_once()

    def test_set_csrf_state_token(self):
        expected_token = "fake-csrf-token"
        with patch.object(
            type(self.wizard_account_id),
            "_get_csrf_state_token",
            autospec=True,
            return_value=expected_token,
        ) as mocked_get_token:
            self.wizard_account_id._set_csrf_state_token()
            value = self.wizard_account_id.csrf_state_token
            mocked_get_token.assert_called_once_with(self.wizard_account_id)
            self.assertEqual(value, expected_token)

    def test_action_associate_social_account(self):
        action_fake_url = {
            "type": "ir.actions.act_url",
            "url": "https://test.example/redirect",
            "target": "self",
        }
        with patch.object(
            type(self.wizard_account_id),
            "_action_valid_add_account",
            autospec=True,
        ) as mocked_valid, patch.object(
            type(self.wizard_account_id),
            "_action_add_account",
            autospec=True,
            return_value=action_fake_url,
        ) as mocked_add:
            result = self.wizard_account_id.action_associate_social_account()
            mocked_valid.assert_called_once_with(self.wizard_account_id)
            mocked_add.assert_called_once_with(self.wizard_account_id)
            self.assertEqual(result, action_fake_url)

    def test_create_account_linkedin_failed(self):
        with self.assertRaises(UserError) as ctx:
            self.SocialAccount._create_account_linkedin(
                "fake-client-id",
                "fake-secret",
                MagicMock(text="Error token"),
            )
        self.assertIn("Creating account", str(ctx.exception))
        self.assertIn("Error token", str(ctx.exception))

    def test_create_account_linkedin_without_access_token(self):
        """A token without an access token used to fail silently."""
        with self.assertRaises(UserError) as ctx:
            self.SocialAccount._create_account_linkedin(
                "fake-client-id",
                "fake-secret",
                {"expires_in": 3600},
            )
        self.assertIn("without an access token", str(ctx.exception))

    def test_linkedin_error_message_explains_the_credentials(self):
        error = Mock(
            text='{"error":"invalid_client",'
            '"error_description":"Client authentication failed"}'
        )
        message = self.SocialAccount._linkedin_error_message(error)
        self.assertIn("Client ID", message)
        self.assertIn("Client Secret", message)

    def test_linkedin_error_message_explains_the_authorization(self):
        error = Mock(
            text='{"error":"invalid_request","error_description":'
            '"Unable to retrieve access token: authorization code not found"}'
        )
        message = self.SocialAccount._linkedin_error_message(error)
        self.assertIn("no longer valid", message)

    def test_linkedin_error_message_uses_the_answer_of_linkedin(self):
        """An unknown error is reported with the words of LinkedIn."""
        error = Mock(
            text='{"serviceErrorCode":100,"message":"Not enough permissions '
            'to access: GET /organizationAcls"}'
        )
        self.assertEqual(
            self.SocialAccount._linkedin_error_message(error),
            "Not enough permissions to access: GET /organizationAcls",
        )

    def test_linkedin_error_message_details_the_rejected_fields(self):
        """A validation error is reported field by field, not as a summary."""
        error = Mock(
            text=(
                '{"code":"MULTIPLE_VALIDATIONS_FAILED","message":"Multiple '
                'errors occurred during the input validation.","errorDetails":'
                '{"inputErrors":[{"description":"/Campaign/runSchedule/start '
                'value 1 must be no earlier than 2"}],'
                '"conditionalInputErrors":[{"description":"/Campaign/status '
                "cannot be set to ARCHIVED if /CampaignGroup/status is set to "
                'DRAFT"}]}}'
            )
        )
        message = self.SocialAccount._linkedin_error_message(error)
        self.assertIn("must be no earlier than", message)
        self.assertIn("cannot be set to ARCHIVED", message)
        self.assertNotIn("Multiple errors", message)

    def test_linkedin_error_message_keeps_an_answer_that_is_not_json(self):
        error = Mock(text="<html>502 Bad Gateway</html>")
        self.assertEqual(
            self.SocialAccount._linkedin_error_message(error),
            "<html>502 Bad Gateway</html>",
        )

    def test_linkedin_error_message_accepts_a_parsed_body(self):
        self.assertEqual(
            self.SocialAccount._linkedin_error_message({"message": "Bad request"}),
            "Bad request",
        )

    def test_create_account_linkedin(self):
        fake_organization = self.generate_magic_mock(
            **{
                "return_value": {
                    "vanityName": "Vanity X",
                }
            }
        )

        def search_side_effect(recordset, domain=None, *args, **kwargs):
            if recordset._name == "wizard.social.account":
                return self.wizard_account_id
            return self.SocialAccount

        with (
            patch(
                "odoo.models.BaseModel.search",
                autospec=True,
                side_effect=search_side_effect,
            ) as mock_search,
            patch(
                "odoo.models.BaseModel.create",
                autospec=True,
                return_value=self.SocialAccountLinkedin,
            ) as mock_create,
            patch("odoo.models.BaseModel.unlink", autospec=True) as mock_unlink,
            patch.object(
                type(self.SocialAccountLinkedin),
                "_get_account_linkedin",
                autospec=True,
                return_value=[fake_organization],
            ) as mock_account_linkedin,
            patch(
                PATCH_ACCOUNT.format("_trigger_initial_sync"),
                autospec=True,
            ) as mock_trigger_sync,
        ):
            self.SocialAccount._create_account_linkedin(
                "fake-client-id",
                "fake-secret",
                {"access_token": "fake-access-token"},
            )
            self.assertEqual(
                mock_search.call_count,
                3,
                msg="The wizard, the account by remote reference and the "
                "account by user name for the rows stored without one.",
            )
            mock_account_linkedin.assert_called_once()
            mock_create.assert_called_once()
            mock_unlink.assert_called_once()
            mock_trigger_sync.assert_called_once()
            self.assertEqual(
                mock_trigger_sync.call_args[0][0],
                self.SocialAccountLinkedin,
                msg="The initial sync only targets the associated accounts.",
            )

    def test_create_account_linkedin_reactivates_archived(self):
        self.SocialAccount.create(
            {
                "name": "Archived Org",
                "username": "archived-org",
                "media_id": self.media_linkedin_id.id,
                "active": False,
            }
        )
        fake_organization = {
            "vanityName": "archived-org",
            "localizedName": "Archived Org",
            "id": "999",
        }
        with (
            patch.object(
                type(self.SocialAccountLinkedin),
                "_get_account_linkedin",
                autospec=True,
                return_value=[fake_organization],
            ),
            patch(
                PATCH_ACCOUNT.format("_trigger_initial_sync"),
                autospec=True,
            ),
        ):
            self.SocialAccount._create_account_linkedin(
                "fake-client-id-2",
                "fake-secret-2",
                {"access_token": "fake-access-token"},
            )
        accounts = self.SocialAccount.with_context(active_test=False).search(
            [("username", "=", "archived-org"), ("media_type", "=", "linkedin")]
        )
        self.assertEqual(len(accounts), 1)
        self.assertTrue(accounts.active)

    def test_create_account_linkedin_stamps_the_last_update(self):
        """The OAuth callback is where the account gets its data back.

        The wizard only writes the keys when they are updated and hands the
        rest over to this flow, so the stamp belongs here.
        """
        account = self.SocialAccountLinkedin
        account.last_update_account = False
        fake_organization = {
            "vanityName": account.username,
            "localizedName": account.name,
            "id": account.remote_ref.split(":")[-1],
        }
        with (
            patch.object(
                type(account),
                "_get_account_linkedin",
                autospec=True,
                return_value=[fake_organization],
            ),
            patch(PATCH_ACCOUNT.format("_trigger_initial_sync"), autospec=True),
        ):
            self.SocialAccount._create_account_linkedin(
                "fake-client-id",
                "fake-secret",
                {"access_token": "fake-access-token"},
            )
        self.assertTrue(account.last_update_account)

    def test_validate_access_token(self):
        patch_notify_user = patch(PATCH_SOCIAL_BASE_MIXIN.format("_notify_user_client"))
        self.SocialAccountLinkedin.expire_access_token_date = (
            datetime.now() + timedelta(days=-10)
        ).date()
        with patch(
            PATCH_ACCOUNT.format("validate_access_token")
        ) as mock_super, patch.object(
            type(self.SocialAccount),
            "_validate_linkedin_access_token",
            autospec=True,
            return_value=True,
        ) as mock_validate_token, patch_notify_user as mock_notify_user:
            self.SocialAccountLinkedin.validate_access_token()
            mock_super.assert_called_once()
            mock_validate_token.assert_called_once()
            mock_notify_user.assert_called_once()

        self.SocialAccountLinkedin.expire_access_token_date = (
            datetime.now() + timedelta(days=30)
        ).date()
        self.SocialAccountLinkedin.refresh_token_expires_in = (
            datetime.now() + timedelta(days=30)
        ).date()
        with patch(
            PATCH_ACCOUNT.format("validate_access_token")
        ) as mock_super_failed, patch_notify_user as mock_notify_user_failed:
            self.SocialAccountLinkedin.validate_access_token()
            mock_super_failed.assert_called_once()
            mock_notify_user_failed.assert_called_once()

    def test_validate_access_token_renews_before_the_expiry_date(self):
        """A token expiring within the margin is renewed, not left to run out."""
        self.SocialAccountLinkedin.expire_access_token_date = (
            datetime.now() + timedelta(days=_TOKEN_MARGIN_DAYS_LINKEDIN - 1)
        ).date()
        self.SocialAccountLinkedin.refresh_token_expires_in = (
            datetime.now() + timedelta(days=200)
        ).date()
        with patch(PATCH_ACCOUNT.format("validate_access_token")), patch.object(
            type(self.SocialAccount),
            "_validate_linkedin_access_token",
            autospec=True,
            return_value=True,
        ) as mock_validate_token, patch(
            PATCH_SOCIAL_BASE_MIXIN.format("_notify_user_client")
        ):
            self.SocialAccountLinkedin.validate_access_token()
        mock_validate_token.assert_called_once()

    def test_validate_access_token_message_is_not_ambiguous(self):
        self.SocialAccountLinkedin.expire_access_token_date = (
            datetime.now() + timedelta(days=-10)
        ).date()
        with patch(PATCH_ACCOUNT.format("validate_access_token")), patch.object(
            type(self.SocialAccount),
            "_validate_linkedin_access_token",
            autospec=True,
            return_value=True,
        ), patch(
            PATCH_SOCIAL_BASE_MIXIN.format("_notify_user_client")
        ) as mock_notify_user:
            self.SocialAccountLinkedin.validate_access_token()
        self.assertEqual(
            mock_notify_user.call_args.kwargs["notif_message"], "The token is valid."
        )
        self.assertEqual(
            mock_notify_user.call_args.kwargs["notif_type"], "social_form_success"
        )

    def test_validate_access_token_without_expiry_dates(self):
        self.SocialAccountLinkedin.write(
            {
                "expire_access_token_date": False,
                "refresh_token_expires_in": False,
            }
        )
        with patch(
            PATCH_ACCOUNT_LINKEDIN.format("_validate_linkedin_access_token"),
            autospec=True,
        ) as mock_validate:
            self.SocialAccountLinkedin.with_context(
                not_notify=True
            ).validate_access_token()
            mock_validate.assert_not_called()

    def test_validate_access_token_expired_uses_context_token(self):
        self.SocialAccountLinkedin.write(
            {
                "expire_access_token_date": "2020-01-01",
                "access_token": False,
            }
        )
        with patch(
            PATCH_ACCOUNT_LINKEDIN.format("_validate_linkedin_access_token"),
            autospec=True,
            return_value=True,
        ) as mock_validate:
            self.SocialAccountLinkedin.with_context(
                not_notify=True, access_token="ctx-token"
            ).validate_access_token()
            mock_validate.assert_called_once()
            self.assertEqual(mock_validate.call_args[0][1], "ctx-token")

    def test_action_validate_access_token_always_asks_linkedin(self):
        """A token can be revoked long before the stored dates expire."""
        self.SocialAccountLinkedin.write(
            {
                "expire_access_token_date": (
                    datetime.now() + timedelta(days=30)
                ).date(),
                "refresh_token_expires_in": (
                    datetime.now() + timedelta(days=60)
                ).date(),
            }
        )
        with patch(
            PATCH_ACCOUNT_LINKEDIN.format("_validate_linkedin_access_token"),
            autospec=True,
            return_value=True,
        ) as mock_validate, patch(
            PATCH_SOCIAL_BASE_MIXIN.format("_notify_user_client")
        ) as mock_notify:
            self.SocialAccountLinkedin.action_validate_access_token()
        mock_validate.assert_called_once()
        self.assertEqual(
            mock_notify.call_args.kwargs["notif_message"], "The token is valid."
        )

    def test_action_validate_access_token_renews_a_revoked_token(self):
        self.SocialAccountLinkedin.write(
            {
                "expire_access_token_date": (
                    datetime.now() + timedelta(days=30)
                ).date(),
                "refresh_token_expires_in": (
                    datetime.now() + timedelta(days=60)
                ).date(),
            }
        )
        with patch(
            PATCH_ACCOUNT_LINKEDIN.format("_validate_linkedin_access_token"),
            autospec=True,
            return_value=False,
        ), patch.object(
            type(self.wizard_account_id), "_update_account", autospec=True
        ) as mock_update:
            self.SocialAccountLinkedin.action_validate_access_token()
        mock_update.assert_called_once()

    def test_validate_access_token_guard_stays_cheap(self):
        """The guard of every API call must not add a request of its own."""
        self.SocialAccountLinkedin.write(
            {
                "expire_access_token_date": (
                    datetime.now() + timedelta(days=30)
                ).date(),
                "refresh_token_expires_in": (
                    datetime.now() + timedelta(days=60)
                ).date(),
            }
        )
        with patch(
            PATCH_ACCOUNT_LINKEDIN.format("_validate_linkedin_access_token"),
            autospec=True,
        ) as mock_validate:
            self.SocialAccountLinkedin.with_context(
                not_notify=True
            ).validate_access_token()
        mock_validate.assert_not_called()

    def test_update_account_does_not_propose_the_client_secret(self):
        """The context of an action is serialized to the browser."""
        action = self.SocialAccountLinkedin.action_update_account()
        self.assertEqual(action["context"]["default_linkedin_client"], "fake-client-id")
        self.assertNotIn("default_linkedin_secret", action["context"])

    def test_update_account_hides_the_client_id_from_a_non_administrator(self):
        """The Client ID is restricted to base.group_system."""
        manager = self.env["res.users"].create(
            {
                "name": "Social manager without system access",
                "login": "social_manager_no_system_test",
                "groups_id": [
                    Command.set(
                        [
                            self.env.ref("base.group_user").id,
                            self.env.ref(
                                "social_media_base.group_social_media_manager"
                            ).id,
                        ]
                    )
                ],
            }
        )
        action = self.SocialAccountLinkedin.with_user(manager).action_update_account()
        self.assertNotIn("default_linkedin_client", action["context"])

    def test_refresh_token_keeps_the_credentials_on_a_json_error(self):
        """LinkedIn answers its errors as JSON too: a dict proves nothing."""
        with patch(
            PATCH_ACCOUNT_LINKEDIN.format("_request_linkedin"),
            autospec=True,
            return_value={"error": "invalid_grant", "error_description": "expired"},
        ), self.assertRaises(UserError):
            self.SocialAccountLinkedin._refresh_token()
        self.assertEqual(self.SocialAccountLinkedin.sudo().access_token, "fake-token")

    def test_refresh_credentials_stores_the_new_token(self):
        fake_response = {
            "access_token": "renewed-access-token",
            "refresh_token": "renewed-refresh-token",
            "expires_in": 60 * 86400,
            "refresh_token_expires_in": 365 * 86400,
        }
        self.SocialAccountLinkedin.sudo().refresh_access_token = "fake-refresh-token"
        with patch(
            PATCH_ACCOUNT_LINKEDIN.format("_request_linkedin"),
            autospec=True,
            return_value=fake_response,
        ):
            self.assertTrue(self.SocialAccountLinkedin._refresh_credentials())
        account_sudo = self.SocialAccountLinkedin.sudo()
        self.assertEqual(account_sudo.access_token, "renewed-access-token")
        self.assertEqual(account_sudo.refresh_access_token, "renewed-refresh-token")
        self.assertEqual(
            account_sudo.expire_access_token_date,
            (datetime.now() + timedelta(days=60)).date(),
        )

    def test_refresh_credentials_without_refresh_token(self):
        """Nothing to renew: the account has to be authorized from the browser."""
        self.SocialAccountLinkedin.sudo().refresh_access_token = False
        self.assertFalse(self.SocialAccountLinkedin._refresh_credentials())

    def test_refresh_credentials_with_an_expired_refresh_token(self):
        self.SocialAccountLinkedin.sudo().refresh_access_token = "fake-refresh-token"
        self.SocialAccountLinkedin.refresh_token_expires_in = (
            datetime.now() - timedelta(days=1)
        ).date()
        self.assertFalse(self.SocialAccountLinkedin._refresh_credentials())

    @mute_logger(LOGGER_ACCOUNT_LINKEDIN)
    def test_refresh_credentials_when_linkedin_refuses_it(self):
        self.SocialAccountLinkedin.sudo().refresh_access_token = "fake-refresh-token"
        with patch(
            PATCH_ACCOUNT_LINKEDIN.format("_request_linkedin"),
            autospec=True,
            return_value={"error": "invalid_grant", "error_description": "expired"},
        ):
            self.assertFalse(self.SocialAccountLinkedin._refresh_credentials())
        self.assertEqual(self.SocialAccountLinkedin.sudo().access_token, "fake-token")

    def test_a_refused_authorization_is_told_apart(self):
        """Only the credentials errors are worth publishing again."""
        with self.assertRaises(SocialCredentialsError):
            self.SocialAccountLinkedin._linkedin_raise_error(
                "The post could not be published on LinkedIn",
                self.generate_magic_mock(status_code=401),
            )
        with self.assertRaises(UserError) as error:
            self.SocialAccountLinkedin._linkedin_raise_error(
                "The post could not be published on LinkedIn",
                {"message": "The commentary is too long"},
            )
        self.assertNotIsInstance(error.exception, SocialCredentialsError)

    def test_unique_account_ignores_the_account_being_updated(self):
        account = self.SocialAccountLinkedin
        account.sudo()._unique_account(
            account.sudo().linkedin_client_id, account.sudo().linkedin_secret
        )
        with self.assertRaises(UserError):
            self.SocialAccount.sudo()._unique_account(
                account.sudo().linkedin_client_id, account.sudo().linkedin_secret
            )

    def test_get_access_token_linkedin_invalid_state(self):
        with self.assertRaises(UserError):
            self.SocialAccountLinkedin._get_access_token_linkedin(
                "CODE", "/web", {"state": "unknown-state"}
            )

    def test_get_access_token_linkedin_state_of_another_user(self):
        other_user = self.env["res.users"].create(
            {
                "name": "Other social user",
                "login": "other_social_user_test",
                "groups_id": [
                    (
                        6,
                        0,
                        [
                            self.env.ref("base.group_user").id,
                            self.env.ref(
                                "social_media_base.group_social_media_user"
                            ).id,
                        ],
                    )
                ],
            }
        )
        with self.assertRaises(UserError):
            self.SocialAccountLinkedin.with_user(other_user)._get_access_token_linkedin(
                "CODE", "/web", {"state": "fake-csrf-token"}
            )

    def test_consume_linkedin_oauth_wizard(self):
        self.SocialAccount._consume_linkedin_oauth_wizard("fake-csrf-token")
        self.assertFalse(self.wizard_account_id.exists())

    def test_get_entity_statistics_does_not_mutate_params(self):
        params_fields = ["q", "organizationalEntity"]
        params_values = {
            "q": "organizationalEntity",
            "organizationalEntity": "urn:li:organization:123456",
        }
        with patch(
            PATCH_ACCOUNT_LINKEDIN.format("_get_share_statistics"),
            autospec=True,
            return_value={},
        ), patch(
            PATCH_ACCOUNT_LINKEDIN.format("_get_ugc_share_statistics"),
            autospec=True,
            return_value={},
        ), patch(
            PATCH_ACCOUNT_LINKEDIN.format("_get_ugc_posts_statistics"),
            autospec=True,
            return_value={},
        ):
            self.SocialAccountLinkedin._get_entity_statistics(
                posts=[{"id": "urn:li:ugcPost:1"}],
                params_fields=params_fields,
                params_values=params_values,
            )
        self.assertEqual(params_fields, ["q", "organizationalEntity"])
        self.assertEqual(
            params_values,
            {
                "q": "organizationalEntity",
                "organizationalEntity": "urn:li:organization:123456",
            },
        )

    def test_get_share_statistics(self):
        self.assertEqual(self.SocialAccountLinkedin._get_share_statistics(), {})
        params_fields = ["q"]
        params_values = {"q": "organizationalEntity"}
        self.assertEqual(
            self.SocialAccountLinkedin._get_share_statistics(
                posts=[{"id": "urn:li:ugcPost:1"}],
                params_fields=params_fields,
                params_values=params_values,
            ),
            {},
            msg="The share endpoint ignores the UGC posts.",
        )
        self.assertNotIn("shares", params_fields)
        response = MagicMock(status_code=200)
        response.json.return_value = {
            "elements": [
                {
                    "share": "urn:li:share:1",
                    "totalShareStatistics": {
                        "clickCount": 1,
                        "likeCount": 2,
                        "commentCount": 3,
                        "shareCount": 4,
                        "engagement": 0.5,
                        "impressionCount": 6,
                    },
                }
            ]
        }
        with patch(
            PATCH_ACCOUNT_LINKEDIN.format("_request_linkedin"),
            autospec=True,
            return_value=response,
        ) as mock_request:
            data = self.SocialAccountLinkedin._get_share_statistics(
                posts=[{"id": "urn:li:share:1"}, {"id": "urn:li:ugcPost:2"}],
                params_fields=params_fields,
                params_values=params_values,
            )
        self.assertEqual(data, {"urn:li:share:1": (1, 2, 3, 4, 0.5, 6)})
        self.assertEqual(
            (params_fields, params_values),
            (["q"], {"q": "organizationalEntity"}),
            msg="The parameters of the caller are left alone.",
        )
        self.assertEqual(
            mock_request.call_args.kwargs["params_values"]["shares"],
            ["urn:li:share:1"],
        )
        self.assertEqual(
            mock_request.call_args.kwargs["endpoint"],
            "/organizationalEntityShareStatistics",
        )
        error_response = MagicMock(status_code=400)
        error_response.json.return_value = {"message": "Invalid share urn"}
        with patch(
            PATCH_ACCOUNT_LINKEDIN.format("_request_linkedin"),
            autospec=True,
            return_value=error_response,
        ):
            with self.assertRaises(UserError):
                self.SocialAccountLinkedin._get_share_statistics(
                    posts=[{"id": "urn:li:share:1"}],
                    params_fields=["q"],
                    params_values={"q": "organizationalEntity"},
                )

    def test_get_ugc_posts_statistics(self):
        self.assertEqual(self.SocialAccountLinkedin._get_ugc_posts_statistics(), {})
        params_fields = ["q"]
        params_values = {"q": "organizationalEntity"}
        self.assertEqual(
            self.SocialAccountLinkedin._get_ugc_posts_statistics(
                posts=[{"id": "urn:li:share:1"}],
                params_fields=params_fields,
                params_values=params_values,
            ),
            {},
            msg="The UGC posts endpoint ignores the shares.",
        )
        self.assertNotIn("ids", params_fields)
        response = MagicMock(status_code=200)
        response.json.return_value = {
            "results": {
                "urn:li:ugcPost:1": {
                    "likesSummary": {"totalLikes": 7},
                    "commentsSummary": {"aggregatedTotalComments": 8},
                }
            }
        }
        with patch(
            PATCH_ACCOUNT_LINKEDIN.format("_request_linkedin"),
            autospec=True,
            return_value=response,
        ) as mock_request:
            data = self.SocialAccountLinkedin._get_ugc_posts_statistics(
                posts=[{"id": "urn:li:ugcPost:1"}, {"id": "urn:li:share:2"}],
                params_fields=params_fields,
                params_values=params_values,
            )
        self.assertEqual(
            data,
            {"urn:li:ugcPost:1": (7, 8)},
            msg="socialActions only knows the likes and the comments.",
        )
        self.assertEqual(
            (params_fields, params_values),
            (["q"], {"q": "organizationalEntity"}),
            msg="The parameters of the caller are left alone.",
        )
        self.assertEqual(
            mock_request.call_args.kwargs["params_values"]["ids"],
            ["urn:li:ugcPost:1"],
        )
        self.assertEqual(mock_request.call_args.kwargs["endpoint"], "/socialActions")
        error_response = MagicMock(status_code=400)
        error_response.json.return_value = {"message": "Invalid ugc post urn"}
        with patch(
            PATCH_ACCOUNT_LINKEDIN.format("_request_linkedin"),
            autospec=True,
            return_value=error_response,
        ):
            with self.assertRaises(UserError):
                self.SocialAccountLinkedin._get_ugc_posts_statistics(
                    posts=[{"id": "urn:li:ugcPost:1"}],
                    params_fields=["q"],
                    params_values={"q": "organizationalEntity"},
                )

    def _fake_urns(self, prefix, count):
        """Return URNs as long as the ones LinkedIn answers."""
        return [f"{prefix}{7132564752928563200 + index}" for index in range(count)]

    def _linkedin_query_string(self, call):
        """Rebuild the query string that a ``_request_linkedin`` call sends."""
        kwargs = call.kwargs
        return "&".join(
            social_url_encode(param_field, kwargs["params_values"])
            for param_field in kwargs["params_fields"]
        )

    def test_batch_urns_by_url_size(self):
        """The batches are cut on the encoded size and lose no URN."""
        urns = self._fake_urns("urn:li:ugcPost:", 250)
        batches = _batch_urns_by_url_size(urns, "ugcPosts")
        self.assertGreater(len(batches), 1)
        for batch in batches:
            self.assertLessEqual(
                _encoded_urns_bytes(batch, "ugcPosts"),
                _QUERY_STRING_MAX_BYTES_LINKEDIN - _QUERY_STRING_MARGIN_BYTES_LINKEDIN,
            )
        self.assertEqual([urn for batch in batches for urn in batch], urns)

    def test_batch_urns_by_url_size_edge_cases(self):
        self.assertEqual(_batch_urns_by_url_size([], "shares"), [])
        self.assertEqual(
            _batch_urns_by_url_size(
                ["urn:li:share:1"],
                "shares",
                _QUERY_STRING_MAX_BYTES_LINKEDIN,
            ),
            [["urn:li:share:1"]],
            msg="A URN that does not fit is still asked for, on its own.",
        )

    def test_get_share_statistics_splits_the_urns(self):
        """A feed of more than a page fits in no single query string."""
        urns = self._fake_urns("urn:li:share:", 250)
        response = MagicMock(status_code=200)
        response.json.return_value = {"elements": []}
        with patch(
            PATCH_ACCOUNT_LINKEDIN.format("_request_linkedin"),
            autospec=True,
            return_value=response,
        ) as mock_request:
            self.SocialAccountLinkedin._get_share_statistics(
                posts=[{"id": urn} for urn in urns],
                params_fields=["q", "organizationalEntity"],
                params_values={
                    "q": "organizationalEntity",
                    "organizationalEntity": "urn:li:organization:123456",
                },
            )
        self.assertGreater(mock_request.call_count, 1)
        asked = []
        for call in mock_request.call_args_list:
            self.assertLess(
                len(self._linkedin_query_string(call).encode()),
                _QUERY_STRING_MAX_BYTES_LINKEDIN,
            )
            asked.extend(call.kwargs["params_values"]["shares"][0].split(","))
        self.assertEqual(asked, urns, msg="Every URN is asked for exactly once.")

    def test_get_ugc_posts_statistics_splits_the_urns(self):
        urns = self._fake_urns("urn:li:ugcPost:", 250)
        response = MagicMock(status_code=200)
        response.json.return_value = {"results": {}}
        with patch(
            PATCH_ACCOUNT_LINKEDIN.format("_request_linkedin"),
            autospec=True,
            return_value=response,
        ) as mock_request:
            self.SocialAccountLinkedin._get_ugc_posts_statistics(
                posts=[{"id": urn} for urn in urns],
                params_fields=[],
                params_values={},
            )
        self.assertGreater(mock_request.call_count, 1)
        asked = []
        for call in mock_request.call_args_list:
            self.assertLess(
                len(self._linkedin_query_string(call).encode()),
                _QUERY_STRING_MAX_BYTES_LINKEDIN,
            )
            asked.extend(call.kwargs["params_values"]["ids"][0].split(","))
        self.assertEqual(asked, urns)

    def test_get_ugc_share_statistics(self):
        """The UGC posts answer the same block of figures as the shares."""
        self.assertEqual(self.SocialAccountLinkedin._get_ugc_share_statistics(), {})
        response = MagicMock(status_code=200)
        response.json.return_value = {
            "elements": [
                {
                    "ugcPost": "urn:li:ugcPost:1",
                    "totalShareStatistics": {
                        "clickCount": 9,
                        "likeCount": 1,
                        "commentCount": 2,
                        "shareCount": 3,
                        "engagement": 0.25,
                        "impressionCount": 40,
                    },
                },
                {"organizationalEntity": "urn:li:organization:123456"},
            ]
        }
        with patch(
            PATCH_ACCOUNT_LINKEDIN.format("_request_linkedin"),
            autospec=True,
            return_value=response,
        ) as mock_request:
            data = self.SocialAccountLinkedin._get_ugc_share_statistics(
                posts=[{"id": "urn:li:ugcPost:1"}, {"id": "urn:li:share:2"}],
                params_fields=["q"],
                params_values={"q": "organizationalEntity"},
            )
        self.assertEqual(
            data,
            {"urn:li:ugcPost:1": (9, 1, 2, 3, 0.25, 40)},
            msg="The aggregate element, which names no entity, is left out.",
        )
        self.assertEqual(
            mock_request.call_args.kwargs["params_values"]["ugcPosts"],
            ["urn:li:ugcPost:1"],
        )
        self.assertEqual(
            mock_request.call_args.kwargs["endpoint"],
            "/organizationalEntityShareStatistics",
        )
        error_response = MagicMock(status_code=400)
        error_response.json.return_value = {"message": "Invalid ugc post urn"}
        with patch(
            PATCH_ACCOUNT_LINKEDIN.format("_request_linkedin"),
            autospec=True,
            return_value=error_response,
        ):
            with self.assertRaises(UserError):
                self.SocialAccountLinkedin._get_ugc_share_statistics(
                    posts=[{"id": "urn:li:ugcPost:1"}],
                    params_fields=["q"],
                    params_values={"q": "organizationalEntity"},
                )

    def test_get_entity_statistics_merges_the_two_ugc_sources(self):
        """A UGC post keeps its figures and takes its likes from the feed."""
        with patch(
            PATCH_ACCOUNT_LINKEDIN.format("_get_share_statistics"),
            autospec=True,
            return_value={"urn:li:share:1": (1, 2, 3, 4, 0.5, 6)},
        ), patch(
            PATCH_ACCOUNT_LINKEDIN.format("_get_ugc_share_statistics"),
            autospec=True,
            return_value={"urn:li:ugcPost:1": (9, 0, 0, 3, 0.25, 40)},
        ), patch(
            PATCH_ACCOUNT_LINKEDIN.format("_get_ugc_posts_statistics"),
            autospec=True,
            return_value={"urn:li:ugcPost:1": (7, 8), "urn:li:ugcPost:2": (1, 2)},
        ) as mock_social_actions:
            data = self.SocialAccountLinkedin._get_entity_statistics(
                posts=[{"id": "urn:li:share:1"}, {"id": "urn:li:ugcPost:1"}]
            )
        self.assertEqual(
            data,
            {
                "urn:li:share:1": (1, 2, 3, 4, 0.5, 6),
                "urn:li:ugcPost:1": (9, 7, 8, 3, 0.25, 40),
                "urn:li:ugcPost:2": (0, 1, 2, 0, 0, 0),
            },
        )
        self.assertEqual(
            mock_social_actions.call_args.kwargs["params_fields"],
            [],
            msg="socialActions takes neither the finder nor the organization.",
        )
        self.assertEqual(mock_social_actions.call_args.kwargs["params_values"], {})

    @mute_logger(LOGGER_ACCOUNT_LINKEDIN)
    def test_update_posts_statistics_isolates_each_account(self):
        """A failing account is rolled back alone, the other one is refreshed."""
        failing = self.SocialAccountLinkedin
        working = self.SocialAccountLinkedinData
        stale = self.SocialPostAccountLinkedin
        ugc_posts = [
            {
                "id": "urn:li:share:other",
                "commentary": "Other post",
                "content": {},
                "publishedAt": 1735689600000,
                "author": "urn:li:organization:123456",
            }
        ]
        (
            patch_validate,
            patch_get_posts,
            patch_all_posts,
            __,
            patch_assets,
            patch_page,
        ) = self._generate_update_posts_statistics_patches(ugc_posts)

        def entity_statistics(account, *args, **kwargs):
            if account.id == failing.id:
                raise UserError(_("LinkedIn refused the statistics"))
            return {}

        patch_entity = self.generate_patch(
            **{
                "model_patch": PATCH_ACCOUNT_LINKEDIN.format("_get_entity_statistics"),
                "side_effect": entity_statistics,
            }
        )
        with patch_validate, patch_get_posts, patch_all_posts, patch_entity, (
            patch_assets
        ), patch_page:
            (failing | working)._update_posts_statistics(False, None)
        self.env.invalidate_all()
        self.assertEqual(
            stale.state,
            "posted",
            msg="The sweep of the failing account was rolled back with it.",
        )
        self.assertTrue(
            working.post_account_ids.filtered(
                lambda line: line.remote_ref == "urn:li:share:other"
            ),
            msg="The account that did not fail was refreshed all the same.",
        )

    def _isolate_linkedin_account(self):
        """Leave ``SocialAccountLinkedin`` as the only LinkedIn account.

        ``_run_check_media_updates`` scans every LinkedIn account, so the
        other accounts have to be archived to know which one the assertions
        are about.
        """
        self.SocialAccount.search(
            [
                ("media_type", "=", "linkedin"),
                ("id", "!=", self.SocialAccountLinkedin.id),
            ]
        ).write({"active": False})

    def _mark_the_page_as_imported(self, accounts=None, statistics=None):
        """Leave on the accounts the mark a previous import would have left."""
        accounts = accounts or self.SocialAccountLinkedin
        accounts.linkedin_statistics_checkpoint = (
            accounts._linkedin_statistics_checkpoint(
                statistics or RECENT_STATISTICS_LINKEDIN
            )
        )

    @contextmanager
    def _patch_recent_statistics(self, statistics=None, side_effect=None):
        """Answer the finder of the daily buckets without calling LinkedIn.

        One patch and one only: the sweep of the pass reads the buckets and
        the check compares against those very buckets, so the whole pass now
        hangs on ``_get_linkedin_daily_statistics``. Patching it alone is what
        makes the number of calls per pass assertable.

        The figures are given in the watched form the assertions are written
        in and handed back as the six-figure buckets the finder answers.

        :param statistics: the watched figures every account answers with.
        :param side_effect: an exception to raise, or a callable taking the
            account and returning its watched figures.
        :return: the mock of ``_get_linkedin_daily_statistics``.
        """
        watched = RECENT_STATISTICS_LINKEDIN if statistics is None else statistics

        def daily_statistics(account, *_args, **_kwargs):
            if side_effect is None:
                return _linkedin_buckets(watched)
            if isinstance(side_effect, BaseException):
                raise side_effect
            return _linkedin_buckets(side_effect(account))

        with self._patch_reader(side_effect=daily_statistics) as mock_reader:
            yield mock_reader

    def test_linkedin_check_days_is_the_window_of_the_check(self):
        """The days compared are the last ones, today included."""
        today = fields.Date.today()
        days = self.SocialAccountLinkedin._linkedin_check_days()
        self.assertEqual(len(days), _UPDATE_CHECK_DAYS_LINKEDIN)
        self.assertEqual(
            max(days),
            today.isoformat(),
            msg="The bucket of today is the one the check is really after.",
        )
        self.assertEqual(
            min(days),
            (today - timedelta(days=_UPDATE_CHECK_DAYS_LINKEDIN - 1)).isoformat(),
        )

    def test_linkedin_watched_figures_trims_the_day_and_the_engagement(self):
        """The sweep reads one day more than the check compares."""
        buckets = _linkedin_buckets(RECENT_STATISTICS_LINKEDIN)
        eighth_day = (
            fields.Date.today() - timedelta(days=_UPDATE_CHECK_DAYS_LINKEDIN)
        ).isoformat()
        buckets[eighth_day] = (9, 9, 9, 9, 0.9, 99)
        self.assertEqual(
            self.SocialAccountLinkedin._linkedin_watched_figures(buckets),
            RECENT_STATISTICS_LINKEDIN,
            msg="The extra day is dropped, and the engagement with it: it is "
            "a ratio of the others, so it moves on its own.",
        )

    def test_linkedin_watched_figures_without_figures(self):
        self.assertEqual(self.SocialAccountLinkedin._linkedin_watched_figures({}), {})

    def test_linkedin_read_watched_figures_asks_the_window_of_the_sweep(self):
        """The import leaves the mark the sweep of a pass would have left."""
        buckets = _linkedin_buckets(RECENT_STATISTICS_LINKEDIN)
        with self._patch_reader(buckets) as mock_reader:
            statistics = self.SocialAccountLinkedin._linkedin_read_watched_figures()
        self.assertEqual(statistics, RECENT_STATISTICS_LINKEDIN)
        start_time, end_time, granularity = mock_reader.call_args.args[1:]
        self.assertEqual(granularity, "DAY")
        self.assertEqual(
            round((end_time - start_time) / (24 * 3600 * 1000)),
            _UPDATE_CHECK_DAYS_LINKEDIN + 1,
            msg="Asked over the window the sweep reads, then trimmed.",
        )
        self.assertGreater(
            end_time,
            epoch_milliseconds(fields.Datetime.now()),
            msg="LinkedIn takes the end of the interval as exclusive and "
            "normalizes it to the day, so a range ending now would leave the "
            "bucket of today out, the one bucket the check is after.",
        )

    def test_linkedin_statistics_snapshot_drops_what_is_not_a_checkpoint(self):
        """Only a mapping of days to lists of numbers reads as a baseline.

        The value comes from a stored column, so everything else has to read
        as "no baseline yet" and reseed instead of comparing wrongly.
        """
        account = self.SocialAccountLinkedin
        for label, stored in (
            ("empty", ""),
            ("not JSON at all", "{not json"),
            ("a JSON list", "[1, 2]"),
            ("a JSON string", '"2025-01-01"'),
            ("a JSON number", "17"),
        ):
            with self.subTest(case=label):
                self.assertEqual(account._linkedin_statistics_snapshot(stored), {})
        # A dict is read, but a day whose figures are not a list of numbers
        # is dropped on its own: the rest of the mark is still usable.
        self.assertEqual(
            account._linkedin_statistics_snapshot(
                '{"2025-01-01": [1, 2.5], "2025-01-02": 12, '
                '"2025-01-03": "12", "2025-01-04": ["12"], '
                '"2025-01-05": {"clicks": 1}, "2025-01-06": null}'
            ),
            {"2025-01-01": [1, 2.5]},
        )

    def test_run_check_media_updates_takes_the_first_reading_as_the_mark(self):
        """An account with no mark yet gets one, and announces nothing."""
        self._isolate_linkedin_account()
        self.SocialAccountLinkedin.linkedin_statistics_checkpoint = False
        with self._patch_recent_statistics(), patch(
            PATCH_ACCOUNT_LINKEDIN.format("_get_posts"), autospec=True
        ) as mock_get_posts:
            self.assertFalse(self.SocialAccount._run_check_media_updates())
        self.assertEqual(
            self.SocialAccountLinkedin.linkedin_statistics_checkpoint,
            self.SocialAccountLinkedin._linkedin_statistics_checkpoint(
                RECENT_STATISTICS_LINKEDIN
            ),
        )
        self.assertFalse(self.SocialAccountLinkedin.need_update)
        mock_get_posts.assert_not_called()

    def test_run_check_media_updates_reads_a_mark_written_before_the_move(self):
        """A checkpoint already stored keeps reading as a baseline.

        The three helpers moved out of ``social_linkedin_utils`` into the
        model without touching the stored form, so a value written by the
        previous version has to compare as it did and not reseed, which
        would flag every active account on the first pass after deploying.
        """
        self._isolate_linkedin_account()
        # Built by hand, in the very form ``json.dumps(sort_keys=True)`` left
        # in the column: the days sorted, keyed by their ISO string, each one
        # carrying its figures as a list of numbers.
        buckets = ", ".join(
            f'"{day}": {list(figures)}'
            for day, figures in sorted(RECENT_STATISTICS_LINKEDIN.items())
        )
        stored = f"{{{buckets}}}"
        self.assertEqual(
            stored,
            self.SocialAccountLinkedin._linkedin_statistics_checkpoint(
                RECENT_STATISTICS_LINKEDIN
            ),
            msg="The move changed the stored form of a checkpoint.",
        )
        self.SocialAccountLinkedin.linkedin_statistics_checkpoint = stored
        with self._patch_recent_statistics(), patch(
            PATCH_ACCOUNT_LINKEDIN.format("_get_posts"),
            autospec=True,
            return_value=[],
        ) as mock_get_posts:
            self.assertFalse(self.SocialAccount._run_check_media_updates())
        self.assertTrue(
            mock_get_posts.called,
            msg="The stored value did not read as a baseline: the check "
            "reseeded instead of comparing.",
        )
        self.assertFalse(self.SocialAccountLinkedin.need_update)
        self.assertEqual(
            self.SocialAccountLinkedin.linkedin_statistics_checkpoint,
            stored,
            msg="A mark that still matches is left as it was.",
        )

    def test_run_check_media_updates_ignores_an_unusable_mark(self):
        """A mark written by an older version is no baseline, and reseeds."""
        self._isolate_linkedin_account()
        self.SocialAccountLinkedin.linkedin_statistics_checkpoint = (
            '{"clickCount": 25, "likeCount": 12}'
        )
        with self._patch_recent_statistics(), patch(
            PATCH_ACCOUNT_LINKEDIN.format("_get_posts"), autospec=True
        ) as mock_get_posts:
            self.assertFalse(self.SocialAccount._run_check_media_updates())
        self.assertEqual(
            self.SocialAccountLinkedin.linkedin_statistics_checkpoint,
            self.SocialAccountLinkedin._linkedin_statistics_checkpoint(
                RECENT_STATISTICS_LINKEDIN
            ),
        )
        self.assertFalse(self.SocialAccountLinkedin.need_update)
        mock_get_posts.assert_not_called()

    def test_run_check_media_updates_when_the_page_moved(self):
        """A page that moved is enough: the feed is not even asked for."""
        self._isolate_linkedin_account()
        self._mark_the_page_as_imported()
        mark = self.SocialAccountLinkedin.linkedin_statistics_checkpoint
        moved = {**RECENT_STATISTICS_LINKEDIN, _linkedin_day(1): (0, 2, 0, 0, 0)}
        with self._patch_recent_statistics(moved), patch(
            PATCH_ACCOUNT_LINKEDIN.format("_get_posts"), autospec=True
        ) as mock_get_posts:
            self.assertTrue(self.SocialAccount._run_check_media_updates())
        self.assertTrue(self.SocialAccountLinkedin.need_update)
        mock_get_posts.assert_not_called()
        self.assertEqual(
            self.SocialAccountLinkedin.linkedin_statistics_checkpoint,
            mark,
            msg="The mark belongs to the import, so the notice does not "
            "clear itself on the next run.",
        )

    def test_run_check_media_updates_notices_the_impressions_alone(self):
        """Views with no interaction are an update too."""
        self._isolate_linkedin_account()
        self._mark_the_page_as_imported()
        moved = {**RECENT_STATISTICS_LINKEDIN, _linkedin_day(2): (5, 0, 0, 0, 30)}
        with self._patch_recent_statistics(moved):
            self.SocialAccount._run_check_media_updates()
        self.assertTrue(self.SocialAccountLinkedin.need_update)

    def test_run_check_media_updates_notices_a_new_day_with_activity(self):
        """A day LinkedIn had nothing for before, now carrying activity."""
        self._isolate_linkedin_account()
        self._mark_the_page_as_imported()
        moved = {**RECENT_STATISTICS_LINKEDIN, _linkedin_day(0): (0, 1, 0, 0, 0)}
        with self._patch_recent_statistics(moved):
            self.SocialAccount._run_check_media_updates()
        self.assertTrue(self.SocialAccountLinkedin.need_update)

    def test_run_check_media_updates_ignores_an_empty_new_day(self):
        """The day in progress starts as a bucket of zeros, not as news."""
        self._isolate_linkedin_account()
        self._mark_the_page_as_imported()
        quiet = {**RECENT_STATISTICS_LINKEDIN, _linkedin_day(0): (0, 0, 0, 0, 0)}
        with self._patch_recent_statistics(quiet), patch(
            PATCH_ACCOUNT_LINKEDIN.format("_get_posts"),
            autospec=True,
            return_value=[{"id": self.SocialPostAccountLinkedin.remote_ref}],
        ):
            self.assertFalse(self.SocialAccount._run_check_media_updates())
        self.assertFalse(self.SocialAccountLinkedin.need_update)

    def test_run_check_media_updates_ignores_a_day_that_aged_out(self):
        """The window slides, so its oldest day leaving is not activity."""
        self._isolate_linkedin_account()
        self._mark_the_page_as_imported()
        slid = {
            period: figures
            for period, figures in RECENT_STATISTICS_LINKEDIN.items()
            if period != _linkedin_day(3)
        }
        with self._patch_recent_statistics(slid), patch(
            PATCH_ACCOUNT_LINKEDIN.format("_get_posts"),
            autospec=True,
            return_value=[{"id": self.SocialPostAccountLinkedin.remote_ref}],
        ):
            self.assertFalse(self.SocialAccount._run_check_media_updates())
        self.assertFalse(self.SocialAccountLinkedin.need_update)

    def test_run_check_media_updates_without_posts(self):
        self._isolate_linkedin_account()
        self._mark_the_page_as_imported()
        with self._patch_recent_statistics(), patch(
            PATCH_ACCOUNT_LINKEDIN.format("_get_posts"),
            autospec=True,
            return_value=[],
        ) as mock_get_posts:
            self.assertFalse(self.SocialAccount._run_check_media_updates())
        self.assertTrue(mock_get_posts.called)
        self.assertFalse(self.SocialAccountLinkedin.need_update)

    def test_run_check_media_updates_with_a_known_post(self):
        """Same figures and nothing new published: nothing to announce."""
        self._isolate_linkedin_account()
        self._mark_the_page_as_imported()
        with self._patch_recent_statistics(), patch(
            PATCH_ACCOUNT_LINKEDIN.format("_get_posts"),
            autospec=True,
            return_value=[{"id": self.SocialPostAccountLinkedin.remote_ref}],
        ):
            self.assertFalse(self.SocialAccount._run_check_media_updates())
        self.assertFalse(self.SocialAccountLinkedin.need_update)

    def test_run_check_media_updates_sees_an_archived_publication(self):
        """Archiving a post does not make its publication new again."""
        self._isolate_linkedin_account()
        self._mark_the_page_as_imported()
        self.SocialPostAccountLinkedin.active = False
        with self._patch_recent_statistics(), patch(
            PATCH_ACCOUNT_LINKEDIN.format("_get_posts"),
            autospec=True,
            return_value=[
                {
                    "id": self.SocialPostAccountLinkedin.with_context(
                        active_test=False
                    ).remote_ref
                }
            ],
        ):
            self.assertFalse(self.SocialAccount._run_check_media_updates())
        self.assertFalse(self.SocialAccountLinkedin.need_update)

    def test_run_check_media_updates_with_unknown_post(self):
        """A publication posted outside Odoo moves no figure of its own."""
        self._isolate_linkedin_account()
        self._mark_the_page_as_imported()
        with self._patch_recent_statistics(), patch(
            PATCH_ACCOUNT_LINKEDIN.format("_get_posts"),
            autospec=True,
            return_value=[{"id": "urn:li:share:not-imported-yet"}],
        ):
            self.SocialAccount._run_check_media_updates()
        self.assertTrue(self.SocialAccountLinkedin.need_update)

    def test_run_check_media_updates_skips_a_flagged_account(self):
        """An account already announcing updates is not checked again."""
        self._isolate_linkedin_account()
        self._mark_the_page_as_imported()
        self.SocialAccountLinkedin.need_update = True
        with self._patch_recent_statistics() as mock_reader, patch(
            PATCH_ACCOUNT_LINKEDIN.format("_check_linkedin_updates"), autospec=True
        ) as mock_check, patch(
            PATCH_ACCOUNT_LINKEDIN.format("_get_posts"), autospec=True
        ) as mock_get_posts:
            self.assertFalse(self.SocialAccount._run_check_media_updates())
        mock_check.assert_not_called()
        mock_get_posts.assert_not_called()
        self.assertEqual(
            mock_reader.call_count,
            1,
            msg="Only the sweep asks: the flag says the user has an import "
            "pending, not that the figures of the page stopped moving.",
        )

    def test_run_check_media_updates_skips_an_account_without_organization(self):
        """The feed of an account with no organization cannot be asked for."""
        self._isolate_linkedin_account()
        self._mark_the_page_as_imported()
        self.SocialAccountLinkedin.remote_ref = False
        self.assertFalse(self.SocialAccountLinkedin.linkedin_account_id)
        with self._patch_recent_statistics() as mock_statistics, patch(
            PATCH_ACCOUNT_LINKEDIN.format("_get_posts"), autospec=True
        ) as mock_get_posts:
            self.assertFalse(self.SocialAccount._run_check_media_updates())
        mock_statistics.assert_not_called()
        mock_get_posts.assert_not_called()

    def test_run_check_media_updates_scans_every_account(self):
        """A flagged account must not stop the scan of the remaining ones."""
        self._isolate_linkedin_account()
        other_account = self.SocialAccountLinkedin.copy(
            {
                "name": "Other LinkedIn",
                "username": "other-linkedin",
                "remote_ref": "urn:li:organization:other",
            }
        )
        self._mark_the_page_as_imported(self.SocialAccountLinkedin | other_account)
        moved = {**RECENT_STATISTICS_LINKEDIN, _linkedin_day(1): (0, 2, 0, 0, 0)}
        with self._patch_recent_statistics(moved):
            self.SocialAccount._run_check_media_updates()
        self.assertTrue(self.SocialAccountLinkedin.need_update)
        self.assertTrue(other_account.need_update)

    @mute_logger(LOGGER_ACCOUNT_LINKEDIN)
    def test_run_check_media_updates_isolates_each_account(self):
        """The account LinkedIn refused must not hide the others."""
        self._isolate_linkedin_account()
        failing = self.SocialAccountLinkedin
        working = failing.copy(
            {
                "name": "Other LinkedIn",
                "username": "other-linkedin",
                "remote_ref": "urn:li:organization:other",
            }
        )
        self._mark_the_page_as_imported(failing | working)

        def recent_statistics(account):
            if account.id == failing.id:
                raise UserError(_("LinkedIn refused the page statistics"))
            return {**RECENT_STATISTICS_LINKEDIN, _linkedin_day(1): (0, 2, 0, 0, 0)}

        with self._patch_recent_statistics(side_effect=recent_statistics):
            self.assertTrue(self.SocialAccount._run_check_media_updates())
        self.assertFalse(failing.need_update)
        self.assertTrue(working.need_update)

    @mute_logger(LOGGER_ACCOUNT_LINKEDIN)
    def test_run_check_media_updates_reraises_a_concurrency_error(self):
        """Odoo keeps its retry: neither handler may swallow the error.

        The inner one re-raises it and the outer one has to let it through,
        because a cron gets no retry of its own.
        """

        class ConcurrencyError(psycopg2.OperationalError):
            pgcode = errorcodes.SERIALIZATION_FAILURE

        self._isolate_linkedin_account()
        self._mark_the_page_as_imported()
        with self._patch_recent_statistics(
            side_effect=ConcurrencyError("serialization conflict")
        ):
            with self.assertRaises(psycopg2.OperationalError):
                self.SocialAccount._run_check_media_updates()

    def test_run_check_media_updates_notifies_the_responsible_user(self):
        self._isolate_linkedin_account()
        self._mark_the_page_as_imported()
        Bus = self.env["bus.bus"]
        with self._patch_recent_statistics(), patch(
            PATCH_ACCOUNT_LINKEDIN.format("_get_posts"),
            autospec=True,
            return_value=[{"id": "urn:li:share:not-imported-yet"}],
        ), patch.object(type(Bus), "_sendone", autospec=True) as patch_sendone:
            self.SocialAccount._run_check_media_updates()
        patch_sendone.assert_called_once()
        self.assertEqual(
            patch_sendone.call_args[0][1],
            self.SocialAccountLinkedin.user_id.partner_id,
        )

    def test_run_check_media_updates_asks_the_finder_once_per_account(self):
        """The check compares what the sweep of the same pass already read."""
        self._isolate_linkedin_account()
        self._mark_the_page_as_imported()
        with self._patch_recent_statistics() as mock_reader, patch(
            PATCH_ACCOUNT_LINKEDIN.format("_get_posts"),
            autospec=True,
            return_value=[{"id": self.SocialPostAccountLinkedin.remote_ref}],
        ):
            self.assertFalse(self.SocialAccount._run_check_media_updates())
        self.assertEqual(
            mock_reader.call_count,
            1,
            msg="The sweep and the check used to ask the same finder for the "
            "same days, a few milliseconds apart.",
        )

    def test_run_check_media_updates_asks_the_finder_once_per_each_account(self):
        """Three eligible accounts, three calls: one apiece and no more."""
        self._isolate_linkedin_account()
        accounts = self.SocialAccountLinkedin
        for index in range(2):
            accounts |= self.SocialAccountLinkedin.copy(
                {
                    "name": f"Other LinkedIn {index}",
                    "username": f"other-linkedin-{index}",
                    "remote_ref": f"urn:li:organization:other-{index}",
                }
            )
        self._mark_the_page_as_imported(accounts)
        with self._patch_recent_statistics() as mock_reader, patch(
            PATCH_ACCOUNT_LINKEDIN.format("_get_posts"),
            autospec=True,
            return_value=[],
        ):
            self.assertFalse(self.SocialAccount._run_check_media_updates())
        self.assertEqual(mock_reader.call_count, len(accounts))

    @mute_logger(LOGGER_ACCOUNT_LINKEDIN)
    def test_run_check_media_updates_skips_the_check_of_a_failed_sweep(self):
        """An account whose reading failed is not asked twice to fail twice."""
        self._isolate_linkedin_account()
        self._mark_the_page_as_imported()
        with self._patch_recent_statistics(
            side_effect=UserError(_("LinkedIn refused the page statistics"))
        ) as mock_reader, patch(
            PATCH_ACCOUNT_LINKEDIN.format("_get_posts"), autospec=True
        ) as mock_get_posts:
            self.assertFalse(self.SocialAccount._run_check_media_updates())
        self.assertEqual(mock_reader.call_count, 1)
        mock_get_posts.assert_not_called()
        self.assertFalse(
            self.SocialAccountLinkedin.need_update,
            msg="A reading that failed says nothing about the page.",
        )

    def test_run_check_media_updates_keeps_a_stored_checkpoint_valid(self):
        """The day the sweep adds is not read as a day that appeared.

        The checkpoints already stored were written with the days the check
        compares. Comparing them against the wider window of the sweep would
        flag every active account at once on the first pass after deploying.
        """
        self._isolate_linkedin_account()
        self._mark_the_page_as_imported()
        eighth_day = (
            fields.Date.today() - timedelta(days=_UPDATE_CHECK_DAYS_LINKEDIN)
        ).isoformat()
        with self._patch_recent_statistics(
            {**RECENT_STATISTICS_LINKEDIN, eighth_day: (7, 7, 7, 7, 77)}
        ), patch(
            PATCH_ACCOUNT_LINKEDIN.format("_get_posts"),
            autospec=True,
            return_value=[{"id": self.SocialPostAccountLinkedin.remote_ref}],
        ):
            self.assertFalse(self.SocialAccount._run_check_media_updates())
        self.assertFalse(self.SocialAccountLinkedin.need_update)

    def test_flag_linkedin_update_is_idempotent(self):
        """The bus message is not pushed again for what is already announced."""
        self.SocialAccountLinkedin.need_update = True
        with patch(
            PATCH_ACCOUNT.format("_need_update"), autospec=True
        ) as mock_need_update:
            self.SocialAccountLinkedin._flag_linkedin_update()
        mock_need_update.assert_not_called()

    @mute_logger(LOGGER_ACCOUNT_LINKEDIN)
    def test_run_check_media_updates_exception(self):
        self._isolate_linkedin_account()
        self._mark_the_page_as_imported()
        with self._patch_recent_statistics(), patch(
            PATCH_ACCOUNT_LINKEDIN.format("_get_posts"),
            autospec=True,
            side_effect=Exception("Error Check Media Updates"),
        ):
            self.assertFalse(self.SocialAccount._run_check_media_updates())
        self.assertFalse(self.SocialAccountLinkedin.need_update)
