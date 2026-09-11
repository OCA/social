# Copyright 2026 Binhex <https://www.binhex.cloud>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).


import base64
from datetime import date, datetime, timedelta
from unittest.mock import MagicMock, Mock, patch

from dateutil.relativedelta import relativedelta

from odoo import _, fields
from odoo.exceptions import UserError
from odoo.fields import Command
from odoo.tests.common import tagged
from odoo.tools import mute_logger

from odoo.addons.social_media_base.exceptions import SocialCredentialsError
from odoo.addons.social_media_base.tests.test_social_common import (
    PATCH_ACCOUNT,
    PATCH_MIXIN_REQUEST,
    PATCH_SOCIAL_BASE_MIXIN,
    PATCH_WIZARD_ACCOUNT,
)
from odoo.addons.social_media_linkedin.social_linkedin_utils import (
    _STATISTICS_HISTORY_MONTHS_LINKEDIN,
    _STATISTICS_MAX_BUCKETS_LINKEDIN,
    _TOKEN_MARGIN_DAYS_LINKEDIN,
    _UPDATE_CHECK_DAYS_LINKEDIN,
    _VIDEO_POLL_ATTEMPTS_MIN_LINKEDIN,
    _VIDEO_POLL_DELAY_MIN_LINKEDIN,
    _VIDEO_POLL_MAX_WAIT_LINKEDIN,
    datetime_from_epoch_milliseconds,
    linkedin_urn_id,
)
from odoo.addons.social_media_linkedin.tests.test_common_linkedin import (
    PATCH_ACCOUNT_LINKEDIN,
    PATCH_WIZARD_ACCOUNT_LINKEDIN,
    RECENT_STATISTICS_LINKEDIN,
    TestSocialCommonLinkedin,
)

LOGGER_ACCOUNT_LINKEDIN = "odoo.addons.social_media_linkedin.models.social_account"


# The figures LinkedIn reports for a whole page day by day, which the check for
# updates watches instead of reading the statistics of every publication. Every
# bucket is (clicks, likes, comments, shares, impressions), the engagement left
# out. Taken from a real account, with its days moved onto the window the check
# compares.


@tagged("post_install", "-at_install")
class TestSocialLinkedin(TestSocialCommonLinkedin):
    """Users are created here, so every module has to be in the registry."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # The uploads read the bytes of the attachment, which is what
        # ``ir.attachment.raw`` holds and ``datas`` answers encoded.
        cls.video_mock = type(
            "Video", (), {"raw": base64.b64decode(cls.video_data), "id": 21}
        )()
        cls.image_mock = type(
            "Image", (), {"raw": base64.b64decode(cls.image_base64), "id": 11}
        )()
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
        self.assertEqual(images, {"11": self.media_image.format("XYZ")})
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
            "social_media_linkedin.video_poll_delay",
            str(_VIDEO_POLL_DELAY_MIN_LINKEDIN),
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

    def test_video_poll_attempts_below_the_minimum(self):
        """A video is asked about at least once, whatever is configured."""
        for written in ("0", "-5"):
            with self.subTest(written=written):
                self.env["ir.config_parameter"].sudo().set_param(
                    "social_media_linkedin.video_poll_attempts", written
                )
                account = self.SocialAccountLinkedin
                attempts = account._linkedin_video_poll_settings()[0]
                self.assertEqual(attempts, _VIDEO_POLL_ATTEMPTS_MIN_LINKEDIN)

    def test_video_poll_delay_below_the_minimum(self):
        """A delay under a second would turn the wait into a burst."""
        self.env["ir.config_parameter"].sudo().set_param(
            "social_media_linkedin.video_poll_delay", "0"
        )
        delay = self.SocialAccountLinkedin._linkedin_video_poll_settings()[1]
        self.assertEqual(delay, _VIDEO_POLL_DELAY_MIN_LINKEDIN)

    def test_video_poll_settings_cap_the_whole_wait(self):
        """What the publication spends inside its transaction is capped."""
        self.env["ir.config_parameter"].sudo().set_param(
            "social_media_linkedin.video_poll_delay", "60"
        )
        self.env["ir.config_parameter"].sudo().set_param(
            "social_media_linkedin.video_poll_attempts", "100000"
        )
        attempts, delay = self.SocialAccountLinkedin._linkedin_video_poll_settings()
        self.assertLessEqual(attempts * delay, _VIDEO_POLL_MAX_WAIT_LINKEDIN)

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
        self.assertEqual(videos, {"21": self.media_video.format("VID123")})
        mock_finalize.assert_called_once_with(
            self.media_video.format("VID123"), "token-123", ["etag-1"]
        )

    def _patch_media_uploads(self, image_urns=None, video_urns=None):
        """Patch both uploads, keying every URN by a made-up attachment id."""
        return (
            patch.object(
                type(self.SocialAccountLinkedin),
                "_linkedin_prepare_images_for_post",
                return_value={
                    str(index): urn for index, urn in enumerate(image_urns or [])
                },
            ),
            patch.object(
                type(self.SocialAccountLinkedin),
                "_linkedin_prepare_videos_for_post",
                return_value={
                    str(index): urn
                    for index, urn in enumerate(video_urns or [], start=100)
                },
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
            post_urn, media_refs = self.SocialAccountLinkedin._linkedin_create_post(
                message="Hello", image_ids=[], video_ids=[]
            )
        self.assertEqual(post_urn, "urn:li:share:1")
        self.assertEqual(list(media_refs.values()), image_urns or [])
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
                media_refs,
            ) = self.SocialAccountLinkedin._linkedin_create_post(
                message="Hello", image_ids=[1], video_ids=[2]
            )
        mock_images.assert_not_called()
        self.assertEqual(
            media_refs,
            {"100": self.media_video.format("1")},
            "The video keeps its URN in media_refs, and no image is uploaded",
        )
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
            (False, {}),
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

    def _patch_daily_statistics(self, elements):
        """Patch the finder answering one bucket per day.

        The window is not patched: the finder is called with the timestamps
        the test gives it, and the day a bucket is filed under comes from its
        own ``timeRange.start``, never from the bounds of the call.
        """
        return self.generate_patch(
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
        )

    def _daily_bucket(self, start, **statistics):
        return {
            "timeRange": {"start": start, "end": start + 86400000},
            "totalShareStatistics": statistics,
        }

    def test_get_linkedin_daily_statistics_keys_the_buckets_by_day(self):
        """Every bucket is keyed by the ISO day of its ``timeRange.start``."""
        patch_request = self._patch_daily_statistics(
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
        patch_request = self._patch_daily_statistics(
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

    # --- The engagement -------------------------------------------------

    def test_the_engagement_is_the_rate_linkedin_documents(self):
        """Forty interactions in a thousand impressions are four per cent.

        The same figure any other social media of the family answers: the
        formula is the one LinkedIn documents for its own ``engagement``, and
        base computes it for everybody.
        """
        self.SocialAccountLinkedin.write({"like_count": 40, "impression_count": 1000})
        self.assertEqual(self.SocialAccountLinkedin.engagement, 0.04)

    def test_the_engagement_counts_what_linkedin_reports(self):
        """The numerator of a LinkedIn account is the four figures it answers.

        ``_interaction_count_fields`` is overridden on the mixin, so once X is
        installed the retweets and the quotes are counters of every account.
        What keeps them out of this rate is that LinkedIn never fills them:
        the buckets of its series carry clicks, likes, comments and shares.
        """
        with self._patch_reader({"2025-01-01": (1, 2, 3, 4, 0.5, 100)}):
            self.SocialAccountLinkedin._snapshot_statistics(
                date(2025, 1, 1), date(2025, 1, 1)
            )
        self.SocialAccountLinkedin._refresh_account_statistics()
        self.assertEqual(self.SocialAccountLinkedin.interactions_count, 10)
        self.assertEqual(self.SocialAccountLinkedin.engagement, 0.1)

    def test_the_engagement_is_derived_from_the_daily_series(self):
        """The rows of the series are the figures LinkedIn reported by day.

        Adding their counters up and dividing is the formula of LinkedIn over
        the numbers of LinkedIn, and it costs no call: the example of its own
        documentation, (109276 + 52 + 70 + 0) / 14490816, comes back out of
        the rows.
        """
        with self._patch_reader(
            {
                "2025-01-01": (109276, 52, 70, 0, 0.007549471334119487, 14490816),
            }
        ):
            self.SocialAccountLinkedin._snapshot_statistics(
                date(2025, 1, 1), date(2025, 1, 1)
            )
        self.SocialAccountLinkedin._refresh_account_statistics()
        self.assertEqual(self.SocialAccountLinkedin.impression_count, 14490816)
        self.assertEqual(self.SocialAccountLinkedin.interactions_count, 109398)
        self.assertAlmostEqual(
            self.SocialAccountLinkedin.engagement, 0.007549471334119487, places=4
        )

    # --- The time series ------------------------------------------------

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

    # --- Chopping the range ---------------------------------------------

    def _asked_days(self, mock_reader):
        """Return the day ranges the finder was asked for, as ISO days.

        The interval of a call ends the day after its last day, so the end is
        moved back to name the last day actually asked for.

        :return: one ``(first_day, last_day)`` pair per call.
        :rtype: list
        """
        asked = []
        for call in mock_reader.call_args_list:
            start_time, end_time = call.args[1:3]
            first = datetime_from_epoch_milliseconds(start_time).date()
            last = datetime_from_epoch_milliseconds(end_time).date() - timedelta(days=1)
            asked.append((first, last))
        return asked

    def test_snapshot_statistics_chops_a_range_wider_than_one_call(self):
        """The endpoint does not paginate, so a wide range is several calls."""
        date_from, date_to = self.SocialAccountLinkedin._linkedin_backfill_window()
        with self._patch_reader() as mock_reader:
            self.SocialAccountLinkedin._snapshot_statistics(date_from, date_to)
        asked = self._asked_days(mock_reader)
        self.assertEqual(
            len(asked),
            4,
            msg="A year of daily buckets does not fit in a single call.",
        )
        self.assertEqual(asked[0][0], date_from)
        self.assertEqual(asked[-1][1], date_to)
        for chunk, following in zip(asked[:-1], asked[1:], strict=True):
            self.assertLessEqual(
                (chunk[1] - chunk[0]).days + 1,
                _STATISTICS_MAX_BUCKETS_LINKEDIN,
                msg="No call may ask for more buckets than the endpoint serves.",
            )
            self.assertEqual(
                following[0],
                chunk[1] + timedelta(days=1),
                msg="The chunks leave neither a gap nor an overlap.",
            )

    def test_snapshot_statistics_keeps_the_refresh_window_in_one_call(self):
        """The window the refresh rewrites fits, so nothing changes for it."""
        date_from, date_to = self.SocialAccountLinkedin._linkedin_refresh_window()
        with self._patch_reader() as mock_reader:
            self.SocialAccountLinkedin._snapshot_statistics(date_from, date_to)
        self.assertEqual(self._asked_days(mock_reader), [(date_from, date_to)])

    def test_snapshot_statistics_merges_the_buckets_of_every_chunk(self):
        """The rows and the answer carry the days of all the chunks."""
        date_from = date(2025, 1, 1)
        date_to = date_from + timedelta(days=_STATISTICS_MAX_BUCKETS_LINKEDIN)

        def one_bucket_per_chunk(account, start_time, _end_time, _granularity):
            day = datetime_from_epoch_milliseconds(start_time).date()
            return {day.isoformat(): (1, 2, 3, 4, 0.5, 100)}

        with self._patch_reader(side_effect=one_bucket_per_chunk):
            buckets = self.SocialAccountLinkedin._snapshot_linkedin_statistics(
                date_from, date_to
            )
        self.assertEqual(
            sorted(buckets),
            [
                date_from.isoformat(),
                (
                    date_from + timedelta(days=_STATISTICS_MAX_BUCKETS_LINKEDIN)
                ).isoformat(),
            ],
            msg="What the caller compares against is the whole range.",
        )
        self.assertEqual(len(self._statistics_of(self.SocialAccountLinkedin)), 2)

    def test_snapshot_statistics_writes_what_a_half_answered_chunk_gave(self):
        """A chunk LinkedIn answers short writes its days and stops none."""
        date_from = date(2025, 1, 1)
        date_to = date_from + timedelta(days=_STATISTICS_MAX_BUCKETS_LINKEDIN)

        def nothing_for_the_first(account, start_time, _end_time, _granularity):
            day = datetime_from_epoch_milliseconds(start_time).date()
            if day == date_from:
                return {}
            return {day.isoformat(): (1, 2, 3, 4, 0.5, 100)}

        with self._patch_reader(side_effect=nothing_for_the_first) as mock_reader:
            self.SocialAccountLinkedin._snapshot_linkedin_statistics(date_from, date_to)
        self.assertEqual(len(mock_reader.call_args_list), 2)
        rows = self._statistics_of(self.SocialAccountLinkedin)
        self.assertEqual(
            rows.mapped("date"),
            [date_from + timedelta(days=_STATISTICS_MAX_BUCKETS_LINKEDIN)],
        )

    # --- Filling the history --------------------------------------------

    def _series_row(self, day, **statistics):
        """Write one row of the time series by hand, no LinkedIn involved."""
        return self.env["social.account.statistics"].create(
            {
                "account_id": self.SocialAccountLinkedin.id,
                "date": day,
                **statistics,
            }
        )

    def test_the_backfill_asks_for_the_whole_history(self):
        """The backfill reaches as far back as LinkedIn may answer."""
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

    def test_the_backfill_is_skipped_when_the_series_reaches_further_back(self):
        """A row older than the refresh window can only come from a backfill."""
        refresh_from = self.SocialAccountLinkedin._linkedin_refresh_window()[0]
        self._series_row(refresh_from - timedelta(days=1), impression_count=10)
        with patch(
            PATCH_ACCOUNT_LINKEDIN.format("_snapshot_statistics"), autospec=True
        ) as mock_snapshot:
            self.SocialAccountLinkedin._backfill_statistics()
        mock_snapshot.assert_not_called()

    def test_the_backfill_runs_when_only_the_refresh_window_is_written(self):
        """The refresh writes those days on every pass, so they prove nothing."""
        refresh_from = self.SocialAccountLinkedin._linkedin_refresh_window()[0]
        self._series_row(refresh_from, impression_count=10)
        with patch(
            PATCH_ACCOUNT_LINKEDIN.format("_snapshot_statistics"), autospec=True
        ) as mock_snapshot:
            self.SocialAccountLinkedin._backfill_statistics()
        mock_snapshot.assert_called_once()

    def test_the_backfill_forced_asks_for_the_period_again(self):
        """What the button passes: the series is there and it is asked anyway."""
        refresh_from = self.SocialAccountLinkedin._linkedin_refresh_window()[0]
        self._series_row(refresh_from - timedelta(days=1), impression_count=10)
        with patch(
            PATCH_ACCOUNT_LINKEDIN.format("_snapshot_statistics"), autospec=True
        ) as mock_snapshot:
            self.SocialAccountLinkedin._backfill_statistics(force=True)
        mock_snapshot.assert_called_once()

    def test_association_fills_the_history_without_a_sync_module(self):
        """The backfill costs a fixed number of calls, so base may ask for it."""
        start, end = self.SocialAccountLinkedin._linkedin_backfill_window()
        with self._patch_reader(
            {
                start.isoformat(): (0, 0, 0, 0, 0.0, 10),
                end.isoformat(): (0, 0, 0, 0, 0.0, 20),
            }
        ):
            self.SocialAccountLinkedin._on_account_associated()
        rows = self._statistics_of(self.SocialAccountLinkedin)
        self.assertIn(
            start,
            rows.mapped("date"),
            msg="Associating an account leaves the year, not the last days.",
        )

    def test_a_failed_backfill_leaves_the_account_associated(self):
        """The association cannot be lost to a history that would not read."""
        with self._patch_reader(side_effect=UserError(_("403 forbidden"))), mute_logger(
            LOGGER_ACCOUNT_LINKEDIN
        ):
            self.SocialAccountLinkedin._on_account_associated()
        self.assertTrue(self.SocialAccountLinkedin.exists())
        self.assertFalse(self._statistics_of(self.SocialAccountLinkedin))

    def test_the_button_asks_for_the_period_again(self):
        """The series is already there and the button asks for it all the same."""
        refresh_from = self.SocialAccountLinkedin._linkedin_refresh_window()[0]
        self._series_row(refresh_from - timedelta(days=1), impression_count=1)
        start = self.SocialAccountLinkedin._linkedin_backfill_window()[0]
        with self._patch_reader({start.isoformat(): (0, 0, 0, 0, 0.0, 42)}):
            self.SocialAccountLinkedin.action_rebuild_statistics_history()
        rows = self._statistics_of(self.SocialAccountLinkedin)
        self.assertIn(
            start,
            rows.mapped("date"),
            msg="What the guard skips is what the button is for.",
        )

    def test_the_button_adds_up_what_it_has_just_written(self):
        """The card is drawn from those rows, so the other order draws stale ones."""
        rows_when_added_up = []
        start = self.SocialAccountLinkedin._linkedin_backfill_window()[0]
        with self._patch_reader(
            {start.isoformat(): (0, 0, 0, 0, 0.0, 42)}
        ), patch.object(
            type(self.SocialAccountLinkedin),
            "_refresh_account_statistics",
            autospec=True,
            side_effect=lambda accounts: rows_when_added_up.append(
                len(self._statistics_of(accounts))
            ),
        ):
            self.SocialAccountLinkedin.action_rebuild_statistics_history()
        self.assertEqual(rows_when_added_up, [1])

    def test_the_backfill_leaves_the_other_media_to_their_connector(self):
        with patch(
            PATCH_ACCOUNT_LINKEDIN.format("_snapshot_statistics"), autospec=True
        ) as mock_snapshot:
            self.social_account_id._backfill_statistics()
        mock_snapshot.assert_not_called()

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
        self.SocialAccountLinkedin.write({"need_update": True})
        with self._patch_recent_statistics():
            self.SocialAccount._run_check_media_updates()
        self.assertEqual(
            len(self._statistics_of(self.SocialAccountLinkedin)),
            len(RECENT_STATISTICS_LINKEDIN),
            msg="A flagged account must not be starved of its time series.",
        )

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
        """The reason LinkedIn refused reaches the user, not a singleton."""
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

    def test_csrf_state_token_is_unguessable(self):
        """A random string, never the same twice.

        The callback resolves the state by equality against the one stored on
        the wizard, so nothing has to be derivable from it.
        """
        token = self.wizard_account_id._get_csrf_state_token()
        self.assertIsInstance(token, str)
        self.assertGreaterEqual(len(token), 32)
        self.assertNotEqual(token, self.wizard_account_id._get_csrf_state_token())

    def test_action_add_account(self):
        with patch.object(
            type(self.wizard_account_id),
            "_get_url_redirect",
            return_value=self.url_callback,
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
        fake_token = "fake-state-token"
        with patch(
            PATCH_WIZARD_ACCOUNT_LINKEDIN.format("secrets.token_urlsafe"),
            autospec=True,
            return_value=fake_token,
        ) as mock_token:
            result = self.wizard_account_id._get_csrf_state_token()
            self.assertEqual(result, fake_token)
            mock_token.assert_called_once()

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
        """A token without an access token is refused, never taken silently."""
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
            patch.object(
                type(self.SocialAccountLinkedin),
                "_on_account_associated",
                autospec=True,
            ) as mock_on_associated,
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
            mock_on_associated.assert_called_once()
            self.assertEqual(
                mock_on_associated.call_args[0][0],
                self.SocialAccountLinkedin,
                msg="The association hook only targets the associated accounts.",
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
            patch.object(
                type(self.SocialAccountLinkedin),
                "_on_account_associated",
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
            "id": linkedin_urn_id(account.remote_ref),
        }
        with (
            patch.object(
                type(account),
                "_get_account_linkedin",
                autospec=True,
                return_value=[fake_organization],
            ),
            patch.object(type(account), "_on_account_associated", autospec=True),
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

    @mute_logger(LOGGER_ACCOUNT_LINKEDIN)
    def test_statistics_failure_of_a_callback_goes_through_the_session(self):
        """Associating an account answers with a redirect that outruns the bus.

        ``_on_account_associated`` reads the figures and fills the daily
        series, both under ``_statistics_guard``, so any refusal of LinkedIn
        at that moment has to be kept in the session instead.
        """
        account = self.SocialAccountLinkedin.with_context(
            social_media_oauth_callback=True
        )
        mock_request = MagicMock(session={})
        with patch(PATCH_MIXIN_REQUEST, new=mock_request), patch.object(
            type(self.env["bus.bus"]), "_sendone", autospec=True
        ) as mock_sendone:
            with account._statistics_guard():
                raise UserError(_("The page role was lost"))
        mock_sendone.assert_not_called()
        kept = mock_request.session["social_media_notification"]
        self.assertEqual(len(kept), 1)
        self.assertIn("The page role was lost", kept[0]["message"])

    @mute_logger(LOGGER_ACCOUNT_LINKEDIN)
    def test_statistics_failure_of_the_cron_goes_through_the_bus(self):
        """Nothing redirects the sweep, so the user is told right away."""
        mock_request = MagicMock(session={})
        sent = []
        with patch(PATCH_MIXIN_REQUEST, new=mock_request), patch.object(
            type(self.env["bus.bus"]),
            "_sendone",
            autospec=True,
            side_effect=lambda bus, channel, notif_type, message: sent.append(message),
        ):
            with self.SocialAccountLinkedin._statistics_guard():
                raise UserError(_("The page role was lost"))
        self.assertEqual(len(sent), 1)
        self.assertIn("The page role was lost", sent[0]["message"])
        self.assertNotIn("social_media_notification", mock_request.session)

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

    def _capture_linkedin_request(self, json_return_value):
        """Patch the HTTP call itself, to see what travels to LinkedIn.

        Patching ``_request_linkedin`` is not enough here: what is asserted is
        where the credentials end up once that method has built the request.
        """
        response = self.generate_magic_mock(
            **{"status_code": 200, "json_return_value": json_return_value}
        )
        return patch(
            f"{LOGGER_ACCOUNT_LINKEDIN}.requests.request", return_value=response
        )

    def test_get_access_token_linkedin_does_not_send_the_secret_in_the_url(self):
        """The token exchange posts the credentials in the body."""
        capture = self._capture_linkedin_request({"access_token": "fake-token"})
        with capture as mock_request:
            self.SocialAccountLinkedin._get_access_token_linkedin(
                "CODE", "/web", {"state": "fake-csrf-token"}
            )
        call_kwargs = mock_request.call_args.kwargs
        self.assertEqual(call_kwargs["method"], "POST")
        self.assertNotIn("?", call_kwargs["url"])
        self.assertNotIn("fake-secret", call_kwargs["url"])
        self.assertEqual(call_kwargs["data"]["client_secret"], "fake-secret")
        self.assertEqual(call_kwargs["data"]["code"], "CODE")
        self.assertFalse(call_kwargs["params"])

    def test_refresh_token_does_not_send_the_secret_in_the_url(self):
        """Renewing the token posts the credentials in the body."""
        self.SocialAccountLinkedin.sudo().write(
            {
                "refresh_access_token": "fake-refresh-token",
                "linkedin_secret": "fake-secret",
            }
        )
        capture = self._capture_linkedin_request({"access_token": "fake-token"})
        with capture as mock_request:
            self.SocialAccountLinkedin._refresh_token()
        call_kwargs = mock_request.call_args.kwargs
        self.assertEqual(call_kwargs["method"], "POST")
        self.assertNotIn("?", call_kwargs["url"])
        self.assertNotIn("fake-secret", call_kwargs["url"])
        self.assertEqual(call_kwargs["data"]["client_secret"], "fake-secret")
        self.assertEqual(call_kwargs["data"]["grant_type"], "refresh_token")
