# Copyright 2025 Binhex <https://www.binhex.cloud>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).


from datetime import datetime, timedelta
from unittest.mock import MagicMock, Mock, patch

from odoo.exceptions import UserError
from odoo.tools import mute_logger

from odoo.addons.social_media_base.social_utils import _generate_timestamps
from odoo.addons.social_media_base.tests.test_social_common import (
    PATCH_ACCOUNT,
    PATCH_SOCIAL_BASE_MIXIN,
    PATCH_WIZARD_ACCOUNT,
)
from odoo.addons.social_media_linkedin.tests.test_common_linkedin import (
    PATCH_ACCOUNT_LINKEDIN,
    PATCH_POST_ACCOUNT_LINKEDIN,
    PATCH_WIZARD_ACCOUNT_LINKEDIN,
    TestSocialCommonLinkedin,
)

LOGGER_ACCOUNT_LINKEDIN = "odoo.addons.social_media_linkedin.models.social_account"


class LinkedinMockMixin:
    def _mock_linkedin(self, return_value, account, attribute="_request_linkedin"):
        return patch.object(type(account), attribute, return_value=return_value)


class TestSocialLinkedin(LinkedinMockMixin, TestSocialCommonLinkedin):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.video_mock = type("Video", (), {"datas": cls.video_data})()
        cls.mediaImage = "urn:li:image:{}"
        cls.mediaVideo = "urn:li:video:{}"

    def test_prepare_url_upload_image(self):
        fake_response = {
            "value": {
                "image": self.mediaImage.format("C123456"),
                "uploadUrl": "https://fake.upload.url/image",
            }
        }

        patch_request_linkedin = self.get_patch_exceptions_linkedin(fake_response)

        with patch_request_linkedin as mock_request:
            image, upload_url = self.SocialAccountLinkedin._prepare_url_upload_image()

            self.assertEqual(image, self.mediaImage.format("C123456"))
            self.assertEqual(upload_url, "https://fake.upload.url/image")

            mock_request.assert_called_once()
            self.assertEqual(
                mock_request.call_args.kwargs["params_values"],
                {"action": "initializeUpload"},
            )

    def test_prepare_url_upload_image_error(self):
        """An answer that is not the registered upload stops the publication."""
        mock_response = self.generate_magic_mock(status_code=403)
        with self.get_patch_exceptions_linkedin(mock_response):
            with self.assertRaises(UserError) as context:
                self.SocialAccountLinkedin._prepare_url_upload_image()
        self.assertIn("UPLOADING IMAGE", str(context.exception))

    def test_prepare_images_for_post_success(self):
        """Every image is registered and uploaded, and its URN is kept."""
        patch_upload_url = patch.object(
            type(self.SocialAccountLinkedin),
            "_prepare_url_upload_image",
            return_value=(
                self.mediaImage.format("XYZ"),
                "https://fake.upload/image",
            ),
        )
        mock_response = self.generate_magic_mock(status_code=201)
        with (
            patch_upload_url,
            self.get_patch_exceptions_linkedin(mock_response) as mock_request,
        ):
            images = self.SocialAccountLinkedin._prepare_images_for_post(
                image_ids=[self.image_base64]
            )
        self.assertEqual(images, [self.mediaImage.format("XYZ")])
        self.assertEqual(mock_request.call_args.kwargs["method"], "PUT")
        self.assertEqual(
            mock_request.call_args.kwargs["complete_url"], "https://fake.upload/image"
        )

    def test_prepare_images_for_post_from_base64_data(self):
        """An image given as a data URL is uploaded as well."""
        patch_upload_url = patch.object(
            type(self.SocialAccountLinkedin),
            "_prepare_url_upload_image",
            return_value=(
                self.mediaImage.format("XYZ"),
                "https://fake.upload/image",
            ),
        )
        mock_response = self.generate_magic_mock(status_code=201)
        with (
            patch_upload_url,
            self.get_patch_exceptions_linkedin(mock_response) as mock_request,
        ):
            images = self.SocialAccountLinkedin._prepare_images_for_post(
                image_datas=f"data:image/png;base64,{self.image_base64}"
            )
        self.assertEqual(images, [self.mediaImage.format("XYZ")])
        self.assertEqual(mock_request.call_args.kwargs["data"], b"testimage")

    def test_prepare_images_for_post_upload_error(self):
        patch_upload_url = patch.object(
            type(self.SocialAccountLinkedin),
            "_prepare_url_upload_image",
            return_value=(
                self.mediaImage.format("XYZ"),
                "https://fake.upload/image",
            ),
        )
        mock_response = self.generate_magic_mock(status_code=400)
        with patch_upload_url, self.get_patch_exceptions_linkedin(mock_response):
            with self.assertRaises(UserError) as context:
                self.SocialAccountLinkedin._prepare_images_for_post(
                    image_ids=[self.image_base64]
                )
        self.assertIn("UPLOADING IMAGE", str(context.exception))

    def test_initialize_video_upload(self):
        fake_response = {
            "value": {
                "video": self.mediaVideo.format("VID123"),
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
        self.assertEqual(video, self.mediaVideo.format("VID123"))
        self.assertEqual(len(instructions), 1)
        self.assertEqual(token, "token-123")
        json_data = mock_request.call_args.kwargs["json_data"]
        self.assertEqual(json_data["initializeUploadRequest"]["fileSizeBytes"], 4)

    def test_initialize_video_upload_error(self):
        mock_response = self.generate_magic_mock(status_code=400)
        with self.get_patch_exceptions_linkedin(mock_response):
            with self.assertRaises(UserError) as context:
                self.SocialAccountLinkedin._linkedin_initialize_video_upload(4)
        self.assertIn("UPLOADING VIDEO", str(context.exception))

    def test_upload_video_parts_keeps_the_order_of_the_etags(self):
        """Each part carries its own slice and its ETag keeps its position."""
        instructions = [
            {"uploadUrl": "https://fake.upload/video/1", "firstByte": 0, "lastByte": 3},
            {"uploadUrl": "https://fake.upload/video/2", "firstByte": 4, "lastByte": 8},
        ]
        first_part = self.generate_magic_mock(status_code=201)
        first_part.headers = {"etag": '"etag-1"'}
        second_part = self.generate_magic_mock(status_code=201)
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

    def test_upload_video_parts_error(self):
        instructions = [
            {"uploadUrl": "https://fake.upload/video/1", "firstByte": 0, "lastByte": 3}
        ]
        mock_response = self.generate_magic_mock(status_code=400)
        with self.get_patch_exceptions_linkedin(mock_response):
            with self.assertRaises(UserError) as context:
                self.SocialAccountLinkedin._linkedin_upload_video_parts(
                    b"1234", instructions
                )
        self.assertIn("UPLOADING VIDEO", str(context.exception))

    def test_finalize_video_upload(self):
        mock_response = self.generate_magic_mock(status_code=200)
        with self.get_patch_exceptions_linkedin(mock_response) as mock_request:
            self.SocialAccountLinkedin._linkedin_finalize_video_upload(
                self.mediaVideo.format("VID123"), "token-123", ["etag-1"]
            )
        json_data = mock_request.call_args.kwargs["json_data"]
        self.assertEqual(
            json_data["finalizeUploadRequest"]["uploadedPartIds"], ["etag-1"]
        )

    def test_finalize_video_upload_error(self):
        mock_response = self.generate_magic_mock(status_code=400)
        with self.get_patch_exceptions_linkedin(mock_response):
            with self.assertRaises(UserError) as context:
                self.SocialAccountLinkedin._linkedin_finalize_video_upload(
                    self.mediaVideo.format("VID123"), "token-123", ["etag-1"]
                )
        self.assertIn("UPLOADING VIDEO", str(context.exception))

    def test_wait_video_available(self):
        """The video is polled until LinkedIn finishes processing it."""
        processing = self.generate_magic_mock(
            status_code=200, json_return_value={"status": "PROCESSING"}
        )
        available = self.generate_magic_mock(
            status_code=200, json_return_value={"status": "AVAILABLE"}
        )
        patch_request = self.get_patch_exceptions_linkedin(
            side_effect=[processing, available]
        )
        with (
            patch_request as mock_request,
            patch(f"{LOGGER_ACCOUNT_LINKEDIN}.time.sleep") as mock_sleep,
        ):
            self.assertTrue(
                self.SocialAccountLinkedin._linkedin_wait_video_available(
                    self.mediaVideo.format("VID123")
                )
            )
        self.assertEqual(mock_request.call_count, 2)
        mock_sleep.assert_called_once()

    def test_wait_video_available_processing_failed(self):
        failed = self.generate_magic_mock(
            status_code=200,
            json_return_value={
                "status": "PROCESSING_FAILED",
                "processingFailureReason": "UNSUPPORTED_FORMAT",
            },
        )
        with self.get_patch_exceptions_linkedin(failed):
            with self.assertRaises(UserError) as context:
                self.SocialAccountLinkedin._linkedin_wait_video_available(
                    self.mediaVideo.format("VID123")
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
            status_code=200, json_return_value={"status": "PROCESSING"}
        )
        with (
            self.get_patch_exceptions_linkedin(processing) as mock_request,
            patch(f"{LOGGER_ACCOUNT_LINKEDIN}.time.sleep"),
        ):
            with self.assertRaises(UserError) as context:
                self.SocialAccountLinkedin._linkedin_wait_video_available(
                    self.mediaVideo.format("VID123")
                )
        self.assertEqual(mock_request.call_count, 2)
        self.assertIn("still processing the video", str(context.exception))

    def test_wait_video_available_error(self):
        mock_response = self.generate_magic_mock(status_code=404)
        with self.get_patch_exceptions_linkedin(mock_response):
            with self.assertRaises(UserError) as context:
                self.SocialAccountLinkedin._linkedin_wait_video_available(
                    self.mediaVideo.format("VID123")
                )
        self.assertIn("GET VIDEO STATUS", str(context.exception))

    def test_video_poll_settings_fall_back_on_a_wrong_parameter(self):
        self.env["ir.config_parameter"].sudo().set_param(
            "social_media_linkedin.video_poll_attempts", "not a number"
        )
        attempts, delay = self.SocialAccountLinkedin._linkedin_video_poll_settings()
        self.assertEqual(attempts, 30)
        self.assertEqual(delay, 2)

    def test_prepare_videos_for_post_success(self):
        """A video is uploaded by parts and published once it is available."""
        patch_initialize = patch.object(
            type(self.SocialAccountLinkedin),
            "_linkedin_initialize_video_upload",
            return_value=(self.mediaVideo.format("VID123"), [{}], "token-123"),
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
            videos = self.SocialAccountLinkedin._prepare_videos_for_post(
                video_ids=[self.video_mock]
            )
        self.assertEqual(videos, [self.mediaVideo.format("VID123")])
        mock_finalize.assert_called_once_with(
            self.mediaVideo.format("VID123"), "token-123", ["etag-1"]
        )

    def _patch_media_uploads(self, image_urns=None, video_urns=None):
        return (
            patch.object(
                type(self.SocialAccountLinkedin),
                "_prepare_images_for_post",
                return_value=image_urns or [],
            ),
            patch.object(
                type(self.SocialAccountLinkedin),
                "_prepare_videos_for_post",
                return_value=video_urns or [],
            ),
        )

    def _linkedin_create_post_payload(self, image_urns=None, video_urns=None):
        """Publish a post and return the body sent to the Posts API."""
        patch_images, patch_videos = self._patch_media_uploads(image_urns, video_urns)
        mock_response = self.generate_magic_mock(status_code=201)
        mock_response.headers = {"x-restli-id": "urn:li:share:1"}
        with (
            patch_images,
            patch_videos,
            self.get_patch_exceptions_linkedin(mock_response) as mock_request,
        ):
            post_urn = self.SocialAccountLinkedin._linkedin_create_post(
                message="Hello", image_ids=[], video_ids=[]
            )
        self.assertEqual(post_urn, "urn:li:share:1")
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
            image_urns=[self.mediaImage.format("1")]
        )
        self.assertEqual(
            json_data["content"], {"media": {"id": self.mediaImage.format("1")}}
        )

    def test_linkedin_create_post_multi_image(self):
        json_data = self._linkedin_create_post_payload(
            image_urns=[self.mediaImage.format("1"), self.mediaImage.format("2")]
        )
        self.assertEqual(
            json_data["content"],
            {
                "multiImage": {
                    "images": [
                        {"id": self.mediaImage.format("1")},
                        {"id": self.mediaImage.format("2")},
                    ]
                }
            },
        )

    def test_linkedin_create_post_video_wins_over_the_images(self):
        """A post carrying a video does not even upload its images."""
        patch_images, patch_videos = self._patch_media_uploads(
            video_urns=[self.mediaVideo.format("1")]
        )
        mock_response = self.generate_magic_mock(status_code=201)
        mock_response.headers = {"x-restli-id": "urn:li:ugcPost:1"}
        with (
            patch_images as mock_images,
            patch_videos,
            self.get_patch_exceptions_linkedin(mock_response) as mock_request,
        ):
            self.SocialAccountLinkedin._linkedin_create_post(
                message="Hello", image_ids=[1], video_ids=[2]
            )
        mock_images.assert_not_called()
        self.assertEqual(
            mock_request.call_args.kwargs["json_data"]["content"],
            {"media": {"id": self.mediaVideo.format("1")}},
        )

    def test_linkedin_create_post_error(self):
        patch_images, patch_videos = self._patch_media_uploads()
        mock_response = self.generate_magic_mock(status_code=422)
        with (
            patch_images,
            patch_videos,
            self.get_patch_exceptions_linkedin(mock_response),
            self.assertRaises(UserError) as context,
        ):
            self.SocialAccountLinkedin._linkedin_create_post(message="Hello")
        self.assertIn("CREATING POST", str(context.exception))

    def test_linkedin_create_post_without_access_token(self):
        self.SocialAccountLinkedin.sudo().access_token = False
        self.assertFalse(
            self.SocialAccountLinkedin._linkedin_create_post(message="Hello")
        )

    def test_get_posts(self):
        mock_response = self.generate_magic_mock(
            status_code=200,
            json_return_value={
                "elements": [
                    {"id": "123", "commentary": "Post 1"},
                    {"id": "456", "commentary": "Post 2"},
                ]
            },
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

        mock_response_failed = self.generate_magic_mock(status_code=400)
        patch_request_linkedin_failed = self.get_patch_exceptions_linkedin(
            mock_response_failed
        )
        with patch_request_linkedin_failed as mock_request_linkedin_failed:
            with self.assertRaises(UserError):
                self.SocialAccountLinkedin._get_posts()
            mock_request_linkedin_failed.assert_called_once()

    def test_get_posts_by_ids(self):
        mock_response = self.generate_magic_mock(
            status_code=200,
            json_return_value={
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
            status_code=200, json_return_value={"elements": []}
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
            status_code=200,
            json_return_value={
                "results": {
                    "urn:li:image:1": {"downloadUrl": "https://fake/1.png"},
                    "urn:li:image:2": {},
                }
            },
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
        mock_response = self.generate_magic_mock(status_code=403)
        with self.get_patch_exceptions_linkedin(mock_response):
            urls = self.SocialAccountLinkedin._get_linkedin_images_download_url(
                ["urn:li:image:1"]
            )
        self.assertEqual(urls, {})
        self.assertEqual(
            self.SocialAccountLinkedin._get_linkedin_images_download_url([]), {}
        )

    def _generate_update_posts_statistics_patches(self, ugc_posts):
        return (
            self.generate_patch(
                model_patch=PATCH_ACCOUNT_LINKEDIN.format("validate_access_token"),
                return_value=True,
            ),
            self.generate_patch(
                model_patch=PATCH_ACCOUNT_LINKEDIN.format("_get_posts"),
                return_value=ugc_posts,
            ),
            self.generate_patch(
                model_patch=PATCH_ACCOUNT_LINKEDIN.format("get_entity_statistics"),
                side_effect=lambda *args, **kwargs: {},
            ),
            self.generate_patch(
                model_patch=PATCH_POST_ACCOUNT_LINKEDIN.format("_get_assets_save"),
                side_effect=lambda *args, **kwargs: None,
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
            patch_entity,
            patch_assets,
        ) = self._generate_update_posts_statistics_patches(ugc_posts)
        with (
            patch_validate,
            patch_get_posts as mock_get_posts,
            patch_entity,
            patch_assets,
        ):
            self.SocialAccountLinkedin._update_posts_statistics(
                "urn:li:share:new", None
            )
            mock_get_posts.assert_called_once()
            self.assertEqual(
                mock_get_posts.call_args.kwargs.get("params_fields"), ["ids"]
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

    def test_update_posts_statistics_full_list_cleans_stale_urns(self):
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
            patch_entity,
            patch_assets,
        ) = self._generate_update_posts_statistics_patches(ugc_posts)
        with patch_validate, patch_get_posts, patch_entity, patch_assets:
            self.SocialAccountLinkedin._update_posts_statistics(False, None)
        self.assertFalse(self.SocialPostAccountLinkedin.remote_ref)
        self.assertFalse(self.SocialPostAccountLinkedin.post_account_url)
        self.assertEqual(self.SocialPostAccountLinkedin.state, "deleted")

    def test_get_chart_account_statistics(self):
        patch_get_default_filter_date = self.generate_patch(
            type_object=True,
            model_patch=self.SocialAccountLinkedin,
            method_patch="_get_default_filter_date",
            return_value=(
                "2025-01-01T00:00:00",
                "2025-01-07T23:59:59",
            ),
        )
        patch_get_entity_statistics = self.generate_patch(
            type_object=True,
            model_patch=self.SocialAccountLinkedin,
            method_patch="get_entity_statistics",
            return_value={
                "urn:li:ugcPost:0119424": (100, 30, 50, 0, 0, 0),
                "urn:li:ugcPost:0115624": (200, 70, 100, 0, 0, 0),
            },
        )

        with patch_get_default_filter_date, patch_get_entity_statistics:
            result = self.SocialAccountLinkedin._get_chart_account_statistics(
                start_date="2025-01-01", end_date="2025-01-07", granularity="WEEK"
            )
            self.assertEqual(len(result), 1)
            self.assertEqual(result[0]["datasets"][0]["data"], [100, 200])
            self.assertEqual(result[0]["datasets"][1]["data"], [0, 0])
            self.assertEqual(result[0]["datasets"][2]["data"], [30, 70])
            self.assertEqual(result[0]["datasets"][3]["data"], [50, 100])
            self.assertEqual(result[0]["datasets"][4]["data"], [0, 0])
            self.assertEqual(result[0]["datasets"][5]["data"], [0, 0])

    def test_get_campaigns(self):
        mock_response = self.generate_magic_mock(
            status_code=200,
            json_return_value={
                "elements": [
                    {"id": "123", "name": "Campaign A"},
                    {"id": "456", "name": "Campaign B"},
                ]
            },
        )

        patch_request_linkedin = self.generate_patch(
            type_object=True,
            model_patch=self.SocialAccountLinkedin,
            method_patch="_request_linkedin",
            return_value=mock_response,
        )

        with patch_request_linkedin as mock_request_linkedin:
            result = self.SocialAccountLinkedin._get_campaigns(
                start_date=self.start_datetime,
                end_date=self.end_datetime,
                campaign_ids=["123"],
            )
            self.assertEqual(len(result), 2)
            self.assertEqual(result[0]["id"], "123")
            self.assertEqual(result[1]["id"], "456")
            mock_request_linkedin.assert_called_once()

        patch_request_linkedin_failed = self.generate_patch(
            type_object=True,
            model_patch=self.SocialAccountLinkedin,
            method_patch="_request_linkedin",
            return_value=self.generate_magic_mock(status_code=403),
        )
        with patch_request_linkedin_failed as mock_request_linkedin_failed:
            with self.assertRaises(UserError):
                self.SocialAccountLinkedin._get_campaigns(
                    start_date=self.start_datetime,
                    end_date=self.end_datetime,
                    campaign_ids=["420"],
                )
            mock_request_linkedin_failed.assert_called_once()

    def test_get_statistics(self):
        mock_response = self.generate_magic_mock(
            status_code=200,
            json_return_value={
                "elements": [
                    {
                        "campaign": "123",
                        "statistics": {"clickCount": 100, "impressionCount": 500},
                    },
                    {
                        "campaign": "456",
                        "statistics": {"clickCount": 200, "impressionCount": 600},
                    },
                ]
            },
        )
        patch_request_linkedin = self.generate_patch(
            type_object=True,
            model_patch=self.SocialAccountLinkedin,
            method_patch="_request_linkedin",
            return_value=mock_response,
        )
        with patch_request_linkedin as mock_request_linkedin:
            result = self.SocialAccountLinkedin._get_statistics(
                ads_ids=["123", "456"],
                start_date=self.start_datetime,
                end_date=self.end_datetime,
            )
            self.assertEqual(len(result), 2)
            self.assertEqual(result[0]["campaign"], "123")
            self.assertEqual(result[1]["campaign"], "456")
            mock_request_linkedin.assert_called_once()

        patch_request_linkedin_failed = self.generate_patch(
            type_object=True,
            model_patch=self.SocialAccountLinkedin,
            method_patch="_request_linkedin",
            return_value=self.generate_magic_mock(status_code=403),
        )
        with patch_request_linkedin_failed as mock_request_linkedin_failed:
            with self.assertRaises(UserError):
                self.SocialAccountLinkedin._get_statistics(
                    ads_ids=["423", "756"],
                    start_date=self.start_datetime,
                    end_date=self.end_datetime,
                )
            mock_request_linkedin_failed.assert_called_once()

    def test_get_statistics_ads(self):
        ads_ids = [123, 456]
        expected_result = [{"mock": "data"}]
        patch_get_statistics = self.generate_patch(
            type_object=True,
            model_patch=self.SocialAccount,
            method_patch="_get_statistics",
            return_value=expected_result,
        )

        with patch_get_statistics as mock_get_statistics:
            result = self.SocialAccountLinkedin._get_statistics_ads(
                ads_ids, self.start_datetime, self.end_datetime
            )
            self.assertEqual(result, expected_result)
            mock_get_statistics.assert_called_once()

    def test_load_ads(self):
        patch_request_linkedin = self.generate_patch(
            type_object=True,
            model_patch=self.SocialAccountLinkedin,
            method_patch="_request_linkedin",
            side_effect=[
                self.generate_magic_mock(
                    status_code=200,
                    json_return_value={
                        "elements": [
                            {
                                "id": "urn:li:sponsoredCreative:1",
                                "content": {"reference": "ref1"},
                                "campaign": "urn:li:sponsoredCampaign:123",
                                "createdAt": 1735689600000,
                                "intendedStatus": "DRAFT",
                                "servingHoldReasons": ["UNDER_REVIEW"],
                                "isTest": True,
                            }
                        ]
                    },
                ),
                self.generate_magic_mock(
                    status_code=200,
                    json_return_value={
                        "results": {
                            "ref1": {
                                "id": "ref1",
                                "commentary": "Test post",
                            }
                        }
                    },
                ),
            ],
        )
        patch_get_campaigns = self.generate_patch(
            model_patch=PATCH_ACCOUNT_LINKEDIN.format("_get_campaigns"),
            return_value=[
                {
                    "id": 123,
                    "account": "urn:li:sponsoredAccount:999",
                }
            ],
        )
        patch_get_statistics_ads = self.generate_patch(
            model_patch=PATCH_ACCOUNT_LINKEDIN.format("_get_statistics_ads"),
            return_value=[
                {
                    "pivotValues": ["urn:li:sponsoredCreative:1"],
                    "clicks": 10,
                }
            ],
        )
        patch_get_default_filter_date = self.generate_patch(
            model_patch=PATCH_ACCOUNT.format("_get_default_filter_date"),
            method_patch="_get_default_filter_date",
            side_effect=(
                lambda s, e, time_date=False: (
                    self.start_datetime,
                    self.end_datetime,
                )
                if not time_date
                else (self.start_datetime, self.end_datetime)
            ),
        )
        patch_ad_account = self.generate_patch(
            model_patch=PATCH_ACCOUNT_LINKEDIN.format("_get_linkedin_ad_account_id"),
            return_value="999",
        )
        with (
            patch_request_linkedin as mock_request_linkedin,
            patch_get_campaigns as mock_get_campaigns,
            patch_get_statistics_ads as mock_get_statistics_ads,
            patch_get_default_filter_date as mock_get_default_filter_date,
            patch_ad_account,
        ):
            result = self.SocialAccountLinkedin._load_ads(
                start_date=self.start_datetime, end_date=self.end_datetime
            )
            self.assertEqual(len(result), 1)
            self.assertEqual(result[0]["id"], "urn:li:sponsoredCreative:1")
            self.assertEqual(result[0]["post"]["name"], "Test post")
            self.assertEqual(result[0]["campaign"]["id"], 123)
            self.assertEqual(result[0]["statistic"]["clicks"], 10)
            self.assertIn("url", result[0])
            # The badge shows the status set by the advertiser, while the
            # reason why LinkedIn is not serving the creative is kept apart.
            self.assertEqual(result[0]["status"], "DRAFT")
            self.assertEqual(result[0]["status_level"], "info")
            self.assertEqual(result[0]["status_detail"], "UNDER_REVIEW")
            self.assertEqual(mock_request_linkedin.call_count, 2)
            mock_get_statistics_ads.assert_called_once()
            mock_get_campaigns.assert_called_once()
            mock_get_default_filter_date.assert_called_once()

        patch_request_linkedin_failed = self.generate_patch(
            type_object=True,
            model_patch=self.SocialAccountLinkedin,
            method_patch="_request_linkedin",
            return_value=self.generate_magic_mock(status_code=403),
        )
        with patch_request_linkedin_failed as mock_request_linkedin_failed:
            with self.assertRaises(UserError):
                self.SocialAccountLinkedin._load_ads(
                    start_date=self.start_datetime, end_date=self.end_datetime
                )
            mock_request_linkedin_failed.assert_called_once()

    def test_load_ads_without_matching_campaign(self):
        patch_request_linkedin = self.generate_patch(
            type_object=True,
            model_patch=self.SocialAccountLinkedin,
            method_patch="_request_linkedin",
            return_value=self.generate_magic_mock(
                status_code=200,
                json_return_value={
                    "elements": [
                        {
                            "id": "urn:li:sponsoredCreative:1",
                            "campaign": "urn:li:sponsoredCampaign:123",
                            "createdAt": 1735689600000,
                            "servingHoldReasons": ["STOPPED"],
                            "isTest": True,
                        }
                    ]
                },
            ),
        )
        patch_get_campaigns = patch(
            PATCH_ACCOUNT_LINKEDIN.format("_get_campaigns"),
            autospec=True,
            return_value=[],
        )
        patch_get_statistics_ads = patch(
            PATCH_ACCOUNT_LINKEDIN.format("_get_statistics_ads"),
            autospec=True,
            return_value=[],
        )
        patch_get_default_filter_date = self.generate_patch(
            model_patch=PATCH_ACCOUNT.format("_get_default_filter_date"),
            method_patch="_get_default_filter_date",
            return_value=(self.start_datetime, self.end_datetime),
        )
        patch_ad_account = self.generate_patch(
            model_patch=PATCH_ACCOUNT_LINKEDIN.format("_get_linkedin_ad_account_id"),
            return_value="999",
        )
        with (
            patch_request_linkedin as mock_request_linkedin,
            patch_get_campaigns as mock_get_campaigns,
            patch_get_statistics_ads as mock_get_statistics_ads,
            patch_get_default_filter_date as mock_get_default_filter_date,
            patch_ad_account,
        ):
            result = self.SocialAccountLinkedin._load_ads(
                start_date=self.start_datetime, end_date=self.end_datetime
            )
            mock_request_linkedin.assert_called_once()
            mock_get_campaigns.assert_called_once()
            mock_get_statistics_ads.assert_called_once()
            mock_get_default_filter_date.assert_called_once()
        self.assertEqual(len(result), 1)
        self.assertEqual(
            result[0]["campaign"],
            {},
            msg="An ad whose campaign is not returned by LinkedIn is kept.",
        )
        self.assertEqual(
            result[0]["status_level"],
            "secondary",
            msg="A status that is not mapped falls back to the neutral badge.",
        )

    @patch(PATCH_ACCOUNT_LINKEDIN.format("_request_linkedin"))
    @patch(PATCH_ACCOUNT_LINKEDIN.format("_get_linkedin_advertising_account"))
    def test_action_import_campaigns(self, mock_advertising, mock_request_linkedin):
        advertising = "urn:li:sponsoredAccount:999"
        mock_advertising.return_value = advertising
        groups_response = MagicMock(status_code=200)
        groups_response.json.return_value = {
            "elements": [
                {
                    "id": 45,
                    "name": "Imported Group",
                    "account": advertising,
                    "totalBudget": {"amount": "100", "currencyCode": "USD"},
                },
                {
                    "id": 46,
                    "name": "Other Account Group",
                    "account": "urn:li:sponsoredAccount:1",
                },
            ],
            "paging": {"total": 2},
        }
        campaigns_response = MagicMock(status_code=200)
        campaigns_response.json.return_value = {
            "elements": [
                {
                    "id": 67,
                    "name": "Imported Campaign",
                    "account": advertising,
                    "campaignGroup": "urn:li:sponsoredCampaignGroup:45",
                    "format": "SINGLE_VIDEO",
                    "unitCost": {"amount": "1", "currencyCode": "USD"},
                    "dailyBudget": {"amount": "10", "currencyCode": "USD"},
                },
            ],
            "paging": {"total": 1},
        }
        creatives_response = MagicMock(status_code=200)
        creatives_response.json.return_value = {
            "elements": [
                {
                    "id": "urn:li:sponsoredCreative:888",
                    "content": {"reference": "urn:li:share:5555"},
                    "campaign": "urn:li:sponsoredCampaign:67",
                    "isTest": True,
                },
            ],
            "metadata": {},
        }
        self.SocialPostAccountLinkedin.write({"remote_ref": "urn:li:share:5555"})
        mock_request_linkedin.side_effect = [
            groups_response,
            campaigns_response,
            creatives_response,
        ]
        res = self.SocialAccountLinkedin.action_import_campaigns()
        self.assertTrue(res["success"])
        self.assertEqual(res["groups"], 1)
        self.assertEqual(res["campaigns"], 1)
        self.assertEqual(res["ads"], 1)
        group = self.env["utm.group.campaign"].search(
            [("remote_ref", "=", "urn:li:sponsoredCampaignGroup:45")]
        )
        self.assertEqual(group.name, "Imported Group")
        self.assertEqual(group.total_budget, 100)
        self.assertFalse(
            self.env["utm.group.campaign"].search(
                [("remote_ref", "=", "urn:li:sponsoredCampaignGroup:46")]
            )
        )
        campaign = self.env["utm.campaign"].search(
            [("remote_ref", "=", "urn:li:sponsoredCampaign:67")]
        )
        self.assertEqual(campaign.campaign_group_id, group)
        self.assertEqual(campaign.account_id, self.SocialAccountLinkedin)
        self.assertEqual(campaign.daily_budget, 10)
        self.assertEqual(campaign.linkedin_format, "SINGLE_VIDEO")
        self.assertEqual(
            self.SocialPostAccountLinkedin.creative_urn,
            "urn:li:sponsoredCreative:888",
        )
        self.assertEqual(group.campaign_count, 1)
        action = group.action_view_campaigns()
        self.assertEqual(action["domain"], [("campaign_group_id", "=", group.id)])
        mock_request_linkedin.side_effect = [
            groups_response,
            campaigns_response,
            creatives_response,
        ]
        res = self.SocialAccountLinkedin.action_import_campaigns()
        self.assertTrue(res["success"])
        self.assertEqual(res["groups"], 0)
        self.assertEqual(res["campaigns"], 0)
        self.assertEqual(res["ads"], 0)

    @patch(PATCH_ACCOUNT_LINKEDIN.format("_request_linkedin"))
    @patch(PATCH_ACCOUNT_LINKEDIN.format("_get_linkedin_advertising_account"))
    def test_campaign_pending_changes_hybrid_import(
        self, mock_advertising, mock_request_linkedin
    ):
        advertising = "urn:li:sponsoredAccount:999"
        mock_advertising.return_value = advertising
        currency_usd = self.env.ref("base.USD")
        group = self.env["utm.group.campaign"].create(
            {
                "name": "Synced Group",
                "remote_ref": "urn:li:sponsoredCampaignGroup:70",
                "total_budget": 100,
                "currency_id": currency_usd.id,
            }
        )
        campaign = self.env["utm.campaign"].create(
            {
                "title": "Synced Campaign",
                "campaign_group_id": group.id,
                "media_id": self.SocialAccountLinkedin.media_id.id,
                "account_id": self.SocialAccountLinkedin.id,
                "unit_cost": 1,
                "daily_budget": 10,
                "remote_ref": "urn:li:sponsoredCampaign:71",
            }
        )
        self.assertFalse(campaign.linkedin_needs_update)
        self.assertFalse(group.linkedin_needs_update)
        campaign.write({"unit_cost": 99})
        group.write({"total_budget": 500})
        self.assertTrue(campaign.linkedin_needs_update)
        self.assertTrue(group.linkedin_needs_update)
        groups_response = MagicMock(status_code=200)
        groups_response.json.return_value = {
            "elements": [
                {
                    "id": 70,
                    "name": "Renamed Group In LinkedIn",
                    "account": advertising,
                    "status": "ACTIVE",
                    "totalBudget": {"amount": "300", "currencyCode": "USD"},
                },
            ],
            "paging": {"total": 1},
        }
        campaigns_response = MagicMock(status_code=200)
        campaigns_response.json.return_value = {
            "elements": [
                {
                    "id": 71,
                    "name": "Renamed Campaign In LinkedIn",
                    "account": advertising,
                    "campaignGroup": "urn:li:sponsoredCampaignGroup:70",
                    "status": "PAUSED",
                    "test": True,
                    "unitCost": {"amount": "5", "currencyCode": "USD"},
                    "dailyBudget": {"amount": "50", "currencyCode": "USD"},
                },
            ],
            "paging": {"total": 1},
        }
        creatives_response = MagicMock(status_code=200)
        creatives_response.json.return_value = {"elements": [], "paging": {"total": 0}}
        mock_request_linkedin.side_effect = [
            groups_response,
            campaigns_response,
            creatives_response,
        ]
        campaign_messages = len(campaign.message_ids)
        group_messages = len(group.message_ids)
        self.SocialAccountLinkedin.action_import_campaigns()
        self.assertEqual(campaign.unit_cost, 99)
        self.assertEqual(campaign.name, "Synced Campaign")
        self.assertEqual(campaign.linkedin_status, "paused")
        self.assertTrue(campaign.linkedin_is_test)
        self.assertTrue(campaign.linkedin_needs_update)
        self.assertEqual(group.total_budget, 500)
        self.assertEqual(group.name, "Synced Group")
        self.assertEqual(group.linkedin_status, "active")
        self.assertTrue(group.linkedin_needs_update)
        self.assertEqual(len(campaign.message_ids), campaign_messages + 1)
        self.assertEqual(len(group.message_ids), group_messages + 1)
        mock_request_linkedin.side_effect = None
        mock_request_linkedin.return_value = MagicMock(status_code=204)
        campaign.action_update_linkedin()
        payload = mock_request_linkedin.call_args.kwargs["json_data"]
        self.assertEqual(payload["patch"]["$set"]["unitCost"]["amount"], "99.0")
        self.assertEqual(
            payload["patch"]["$set"]["campaignGroup"],
            "urn:li:sponsoredCampaignGroup:70",
        )
        self.assertFalse(campaign.linkedin_needs_update)
        group.action_update_linkedin()
        payload = mock_request_linkedin.call_args.kwargs["json_data"]
        self.assertEqual(payload["patch"]["$set"]["totalBudget"]["amount"], "500.0")
        self.assertFalse(group.linkedin_needs_update)
        mock_request_linkedin.side_effect = [
            groups_response,
            campaigns_response,
            creatives_response,
        ]
        self.SocialAccountLinkedin.action_import_campaigns()
        self.assertEqual(campaign.unit_cost, 5)
        self.assertEqual(group.total_budget, 300)
        self.assertEqual(group.name, "Renamed Group In LinkedIn")
        self.assertFalse(campaign.linkedin_needs_update)
        self.assertFalse(group.linkedin_needs_update)

    @patch(PATCH_ACCOUNT_LINKEDIN.format("_request_linkedin"))
    @patch(PATCH_ACCOUNT_LINKEDIN.format("_get_linkedin_advertising_account"))
    def test_group_publish_linkedin(self, mock_advertising, mock_request_linkedin):
        mock_advertising.return_value = "urn:li:sponsoredAccount:999"
        group = self.env["utm.group.campaign"].create(
            {
                "name": "Standalone Group",
                "total_budget": 100,
                "currency_id": self.env.ref("base.USD").id,
            }
        )
        mock_request_linkedin.return_value = MagicMock(
            status_code=201, headers={"Location": "/adCampaignGroupsV2/555"}
        )
        group.action_publish_linkedin()
        self.assertEqual(group.remote_ref, "urn:li:sponsoredCampaignGroup:555")
        self.assertEqual(group.linkedin_status, "draft")
        self.assertFalse(group.linkedin_needs_update)
        payload = mock_request_linkedin.call_args.kwargs["json_data"]
        self.assertEqual(payload["status"], "DRAFT")
        self.assertEqual(payload["totalBudget"]["amount"], "100.0")
        with self.assertRaises(UserError):
            group.action_publish_linkedin()
        empty_group = self.env["utm.group.campaign"].create({"name": "Empty Group"})
        with self.assertRaises(UserError):
            empty_group.action_publish_linkedin()

    def test_deleted_on_linkedin_history_message(self):
        currency_usd = self.env.ref("base.USD")
        group = self.env["utm.group.campaign"].create(
            {
                "name": "History Group",
                "remote_ref": "urn:li:sponsoredCampaignGroup:90",
                "total_budget": 100,
                "currency_id": currency_usd.id,
                "linkedin_status": "active",
            }
        )
        campaign = self.env["utm.campaign"].create(
            {
                "title": "History Campaign",
                "campaign_group_id": group.id,
                "media_id": self.SocialAccountLinkedin.media_id.id,
                "account_id": self.SocialAccountLinkedin.id,
                "unit_cost": 1,
                "daily_budget": 10,
                "remote_ref": "urn:li:sponsoredCampaign:91",
                "linkedin_status": "active",
            }
        )
        group_messages = len(group.message_ids)
        campaign_messages = len(campaign.message_ids)
        elements_group = [
            {
                "id": 90,
                "name": "History Group",
                "status": "PENDING_DELETION",
                "totalBudget": {"amount": "100", "currencyCode": "USD"},
            }
        ]
        elements_campaign = [
            {
                "id": 91,
                "name": "History Campaign",
                "status": "REMOVED",
                "campaignGroup": "urn:li:sponsoredCampaignGroup:90",
                "unitCost": {"amount": "1", "currencyCode": "USD"},
                "dailyBudget": {"amount": "10", "currencyCode": "USD"},
            }
        ]
        self.SocialAccountLinkedin._upsert_linkedin_campaigns(
            elements_group, elements_campaign
        )
        self.assertEqual(group.linkedin_status, "pending_deletion")
        self.assertEqual(campaign.linkedin_status, "removed")
        self.assertEqual(len(group.message_ids), group_messages + 1)
        self.assertEqual(len(campaign.message_ids), campaign_messages + 1)
        self.SocialAccountLinkedin._upsert_linkedin_campaigns(
            elements_group, elements_campaign
        )
        self.assertEqual(len(group.message_ids), group_messages + 1)
        self.assertEqual(len(campaign.message_ids), campaign_messages + 1)

    def test_campaign_locked_linkedin_statuses(self):
        currency_usd = self.env.ref("base.USD")
        group = self.env["utm.group.campaign"].create(
            {
                "name": "Locked Group",
                "remote_ref": "urn:li:sponsoredCampaignGroup:80",
                "total_budget": 100,
                "currency_id": currency_usd.id,
            }
        )
        campaign = self.env["utm.campaign"].create(
            {
                "title": "Locked Campaign",
                "campaign_group_id": group.id,
                "media_id": self.SocialAccountLinkedin.media_id.id,
                "account_id": self.SocialAccountLinkedin.id,
                "unit_cost": 1,
                "daily_budget": 10,
                "remote_ref": "urn:li:sponsoredCampaign:81",
            }
        )
        campaign.linkedin_status = "canceled"
        group.linkedin_status = "pending_deletion"
        with self.assertRaises(UserError):
            campaign.write({"unit_cost": 5})
        with self.assertRaises(UserError):
            campaign.action_update_linkedin()
        with self.assertRaises(UserError):
            group.write({"total_budget": 200})
        with self.assertRaises(UserError):
            group.action_update_linkedin()
        campaign.with_context(skip_linkedin_needs_update=True).write({"unit_cost": 5})
        group.with_context(skip_linkedin_needs_update=True).write({"total_budget": 200})
        self.assertEqual(campaign.unit_cost, 5)
        self.assertEqual(group.total_budget, 200)
        campaign.linkedin_status = "paused"
        campaign.write({"unit_cost": 7})
        self.assertTrue(campaign.linkedin_needs_update)

    @patch(PATCH_ACCOUNT_LINKEDIN.format("_request_linkedin"))
    def test_validate_linkedin_access_token(self, mock_request_linkedin):
        mock_request_linkedin.return_value = {"active": True}
        result = self.SocialAccountLinkedin.validate_linkedin_access_token("token")
        self.assertTrue(result)

        mock_request_linkedin.return_value = {"active": False}
        result = self.SocialAccountLinkedin.validate_linkedin_access_token("token")
        self.assertFalse(result)

        self.assertEqual(mock_request_linkedin.call_count, 2)

    def test_get_default_filter_date(self):
        start_date = datetime.now()
        end_date = start_date + timedelta(days=30)
        result = self.SocialAccountLinkedinData._get_default_filter_date(
            start_date=start_date,
            end_date=end_date,
            time_date=True,
        )
        self.assertEqual(
            result,
            _generate_timestamps(date_start=start_date, date_end=end_date),
            msg="With time_date the dates come back as millisecond timestamps.",
        )
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

    @patch(PATCH_ACCOUNT_LINKEDIN.format("_load_ads"))
    @patch(PATCH_ACCOUNT_LINKEDIN.format("search"))
    def test_load_ads_accounts(self, mock_search, mock_load_ads):
        # ``_load_ads`` is chained straight into the payload, so its return
        # value must be the list of ads, not an object carrying one.
        ads_linkedin = [
            {
                "media_type": "linkedin",
                "statistic": {"clicks": 10},
            }
        ]
        mock_load_ads.return_value = ads_linkedin
        mock_search.return_value = [self.SocialAccountLinkedin]
        res = self.SocialAccount._load_ads_accounts()
        self.assertEqual(mock_search.call_count, 1)
        self.assertEqual(res["ads"], ads_linkedin)

    @patch(PATCH_ACCOUNT_LINKEDIN.format("_load_ads"))
    @patch(PATCH_ACCOUNT_LINKEDIN.format("search"))
    def test_load_ads_accounts_without_accounts(self, mock_search, mock_load_ads):
        """With no LinkedIn account the payload keeps ``ads`` as a list."""
        mock_search.return_value = self.SocialAccount.browse()
        res = self.SocialAccount._load_ads_accounts()
        self.assertEqual(res["ads"], [])
        mock_load_ads.assert_not_called()

    def test_unique_account(self):
        with self.assertRaises(UserError):
            self.SocialAccountLinkedin.unique_account(
                linkedin_client_id="fake-client-id", linkedin_secret="fake-secret"
            )

    def test_update_account(self):
        res = self.SocialAccountLinkedin.update_account()
        self.assertEqual(res["context"]["default_linkedin_client"], "fake-client-id")
        self.assertEqual(res["context"]["default_linkedin_secret"], "fake-secret")

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
        result = self.SocialAccountLinkedin.get_access_token_linkedin(
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
            res = self.SocialAccount.get_account_linkedin("fake-access-token")
            self.assertEqual(res[0]["id"], organization_id)
            self.assertEqual(res[0]["localizedName"], organization_name)
            self.assertEqual(res[0]["vanityName"], organization_name)
            self.assertTrue(res[0]["logo"])
            self.assertEqual(mock_request.call_count, 3)

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
            res = self.SocialAccount.get_account_linkedin("fake-access-token")
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
        with (
            patch.object(
                type(self.wizard_account_id),
                "_get_url_redirect",
                return_value=self.url_callback,
            ),
            patch.object(
                type(self.wizard_account_id),
                "_generate_code",
                return_value="fake-code-token",
            ),
        ):
            result = self.wizard_account_id._action_add_account()
            self.assertIn("fake-client-id", result["url"])
            self.assertEqual(result["type"], "ir.actions.act_url")

            result = self.wizard_account_id.with_context(
                only_url=True
            )._action_add_account()
            self.assertIn("fake-client-id", result)

    def test_action_valid_add_account(self):
        with patch.object(type(self.SocialAccount), "unique_account") as uni_acc:
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
            }
        )
        result = self.wizard_account_id._update_account()
        self.assertEqual(result["type"], "ir.actions.act_url")
        self.assertEqual(result["target"], "self")
        self.assertEqual(
            self.SocialAccountLinkedin.linkedin_client_id,
            self.wizard_account_id.linkedin_client,
        )
        self.assertEqual(
            self.SocialAccountLinkedin.linkedin_secret,
            self.wizard_account_id.linkedin_secret,
        )

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

    @patch(PATCH_ACCOUNT_LINKEDIN.format("get_account_linkedin"))
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
        with (
            patch.object(
                type(self.wizard_account_id), "_generate_code", autospec=True
            ) as mock_fake_code,
            patch(
                PATCH_WIZARD_ACCOUNT_LINKEDIN.format("hmac"),
                autospec=True,
                return_value=fake_code_hmac,
            ) as mock_hmac,
        ):
            result = self.wizard_account_id._get_csrf_state_token()
            self.assertEqual(result, fake_code_hmac)
            mock_hmac.assert_called_once()
            mock_fake_code.assert_called_once()

        with patch(
            PATCH_WIZARD_ACCOUNT.format("_get_csrf_state_token"), autospec=True
        ) as mock_hmac_super:
            self.WizardAccount._get_csrf_state_token()
            mock_hmac_super.assert_called_once()

    def test_compute_csrf_state_token(self):
        expected_token = "fake-csrf-token"
        with patch.object(
            type(self.wizard_account_id),
            "_get_csrf_state_token",
            autospec=True,
            return_value=expected_token,
        ) as mocked_get_token:
            self.wizard_account_id._compute_csrf_state_token()
            value = self.wizard_account_id.csrf_state_token
            mocked_get_token.assert_called_once_with(self.wizard_account_id)
            self.assertEqual(value, expected_token)

    def test_action_associate_social_account(self):
        action_fake_url = {
            "type": "ir.actions.act_url",
            "url": "https://test.example/redirect",
            "target": "self",
        }
        with (
            patch.object(
                type(self.wizard_account_id),
                "_action_valid_add_account",
                autospec=True,
            ) as mocked_valid,
            patch.object(
                type(self.wizard_account_id),
                "_action_add_account",
                autospec=True,
                return_value=action_fake_url,
            ) as mocked_add,
        ):
            result = self.wizard_account_id.action_associate_social_account()
            mocked_valid.assert_called_once_with(self.wizard_account_id)
            mocked_add.assert_called_once_with(self.wizard_account_id)
            self.assertEqual(result, action_fake_url)

    def test_create_account_linkedin_failed(self):
        with self.assertRaises(UserError) as ctx:
            self.SocialAccount.create_account_linkedin(
                "fake-client-id",
                "fake-secret",
                MagicMock(text="Error token"),
            )
        self.assertIn("Creating account", str(ctx.exception))
        self.assertIn("Error token", str(ctx.exception))

    def test_create_account_linkedin_without_access_token(self):
        """A token without an access token used to fail silently."""
        with self.assertRaises(UserError) as ctx:
            self.SocialAccount.create_account_linkedin(
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
            return_value={
                "vanityName": "Vanity X",
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
                "get_account_linkedin",
                autospec=True,
                return_value=[fake_organization],
            ) as mock_account_linkedin,
            patch(
                PATCH_ACCOUNT.format("_trigger_initial_sync"),
                autospec=True,
            ) as mock_trigger_sync,
        ):
            self.SocialAccount.create_account_linkedin(
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
                "get_account_linkedin",
                autospec=True,
                return_value=[fake_organization],
            ),
            patch(
                PATCH_ACCOUNT.format("_trigger_initial_sync"),
                autospec=True,
            ),
        ):
            self.SocialAccount.create_account_linkedin(
                "fake-client-id-2",
                "fake-secret-2",
                {"access_token": "fake-access-token"},
            )
        accounts = self.SocialAccount.with_context(active_test=False).search(
            [("username", "=", "archived-org"), ("media_type", "=", "linkedin")]
        )
        self.assertEqual(len(accounts), 1)
        self.assertTrue(accounts.active)

    def test_validate_access_token(self):
        patch_notify_user = patch(PATCH_SOCIAL_BASE_MIXIN.format("_notify_user_client"))
        self.SocialAccountLinkedin.expire_access_token_date = (
            datetime.now() + timedelta(days=-10)
        ).date()
        with (
            patch(PATCH_ACCOUNT.format("validate_access_token")) as mock_super,
            patch.object(
                type(self.SocialAccount),
                "validate_linkedin_access_token",
                autospec=True,
                return_value=True,
            ) as mock_validate_token,
            patch_notify_user as mock_notify_user,
        ):
            self.SocialAccountLinkedin.validate_access_token()
            mock_super.assert_called_once()
            mock_validate_token.assert_called_once()
            mock_notify_user.assert_called_once()

        self.SocialAccountLinkedin.expire_access_token_date = (
            datetime.now() + timedelta(days=1)
        ).date()
        self.SocialAccountLinkedin.refresh_token_expires_in = (
            datetime.now() + timedelta(days=1)
        ).date()
        with (
            patch(PATCH_ACCOUNT.format("validate_access_token")) as mock_super_failed,
            patch_notify_user as mock_notify_user_failed,
        ):
            self.SocialAccountLinkedin.validate_access_token()
            mock_super_failed.assert_called_once()
            mock_notify_user_failed.assert_called_once()

    def test_validate_access_token_message_is_not_ambiguous(self):
        self.SocialAccountLinkedin.expire_access_token_date = (
            datetime.now() + timedelta(days=-10)
        ).date()
        with (
            patch(PATCH_ACCOUNT.format("validate_access_token")),
            patch.object(
                type(self.SocialAccount),
                "validate_linkedin_access_token",
                autospec=True,
                return_value=True,
            ),
            patch(
                PATCH_SOCIAL_BASE_MIXIN.format("_notify_user_client")
            ) as mock_notify_user,
        ):
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
            PATCH_ACCOUNT_LINKEDIN.format("validate_linkedin_access_token"),
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
            PATCH_ACCOUNT_LINKEDIN.format("validate_linkedin_access_token"),
            autospec=True,
            return_value=True,
        ) as mock_validate:
            self.SocialAccountLinkedin.with_context(
                not_notify=True, access_token="ctx-token"
            ).validate_access_token()
            mock_validate.assert_called_once()
            self.assertEqual(mock_validate.call_args[0][1], "ctx-token")

    def test_get_access_token_linkedin_invalid_state(self):
        with self.assertRaises(UserError):
            self.SocialAccountLinkedin.get_access_token_linkedin(
                "CODE", "/web", {"state": "unknown-state"}
            )

    def test_get_access_token_linkedin_state_of_another_user(self):
        other_user = self.env["res.users"].create(
            {
                "name": "Other social user",
                "login": "other_social_user_test",
                "group_ids": [
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
            self.SocialAccountLinkedin.with_user(other_user).get_access_token_linkedin(
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
        with (
            patch(
                PATCH_ACCOUNT_LINKEDIN.format("get_share_statistics"),
                autospec=True,
                return_value={},
            ),
            patch(
                PATCH_ACCOUNT_LINKEDIN.format("get_ugc_posts_statistics"),
                autospec=True,
                return_value={},
            ),
        ):
            self.SocialAccountLinkedin.get_entity_statistics(
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
        self.assertEqual(self.SocialAccountLinkedin.get_share_statistics(), {})
        params_fields = ["q"]
        params_values = {"q": "organizationalEntity"}
        self.assertEqual(
            self.SocialAccountLinkedin.get_share_statistics(
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
            data = self.SocialAccountLinkedin.get_share_statistics(
                posts=[{"id": "urn:li:share:1"}, {"id": "urn:li:ugcPost:2"}],
                params_fields=params_fields,
                params_values=params_values,
            )
        self.assertEqual(data, {"urn:li:share:1": (1, 2, 3, 4, 0.5, 6)})
        self.assertEqual(params_values["shares"], ["urn:li:share:1"])
        self.assertEqual(
            mock_request.call_args.kwargs["endpoint"],
            "/organizationalEntityShareStatistics",
        )
        error_response = MagicMock(status_code=400)
        error_response.json.return_value = {"message": "Invalid share urn"}
        with (
            patch(
                PATCH_ACCOUNT_LINKEDIN.format("_request_linkedin"),
                autospec=True,
                return_value=error_response,
            ),
            self.assertRaises(UserError),
        ):
            self.SocialAccountLinkedin.get_share_statistics(
                posts=[{"id": "urn:li:share:1"}],
                params_fields=["q"],
                params_values={"q": "organizationalEntity"},
            )

    def test_get_ugc_posts_statistics(self):
        self.assertEqual(self.SocialAccountLinkedin.get_ugc_posts_statistics(), {})
        params_fields = ["q"]
        params_values = {"q": "organizationalEntity"}
        self.assertEqual(
            self.SocialAccountLinkedin.get_ugc_posts_statistics(
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
            data = self.SocialAccountLinkedin.get_ugc_posts_statistics(
                posts=[{"id": "urn:li:ugcPost:1"}, {"id": "urn:li:share:2"}],
                params_fields=params_fields,
                params_values=params_values,
            )
        self.assertEqual(data, {"urn:li:ugcPost:1": (0, 7, 8, 0, 0, 0)})
        self.assertEqual(params_values["ids"], ["urn:li:ugcPost:1"])
        self.assertEqual(mock_request.call_args.kwargs["endpoint"], "/socialActions")
        error_response = MagicMock(status_code=400)
        error_response.json.return_value = {"message": "Invalid ugc post urn"}
        with (
            patch(
                PATCH_ACCOUNT_LINKEDIN.format("_request_linkedin"),
                autospec=True,
                return_value=error_response,
            ),
            self.assertRaises(UserError),
        ):
            self.SocialAccountLinkedin.get_ugc_posts_statistics(
                posts=[{"id": "urn:li:ugcPost:1"}],
                params_fields=["q"],
                params_values={"q": "organizationalEntity"},
            )

    def _isolate_linkedin_account(self):
        """Leave ``SocialAccountLinkedin`` as the only LinkedIn account.

        ``_run_check_media_updates`` scans every LinkedIn account and returns
        on the first one needing an update, so the other accounts have to be
        archived to know which one the assertions are about.
        """
        self.SocialAccount.search(
            [
                ("media_type", "=", "linkedin"),
                ("id", "!=", self.SocialAccountLinkedin.id),
            ]
        ).write({"active": False})

    def test_run_check_media_updates_without_posts(self):
        self._isolate_linkedin_account()
        with patch(
            PATCH_ACCOUNT_LINKEDIN.format("_get_posts"),
            autospec=True,
            return_value=[],
        ) as mock_get_posts:
            self.assertFalse(self.SocialAccount._run_check_media_updates())
        self.assertTrue(mock_get_posts.called)
        self.assertFalse(self.SocialAccountLinkedin.need_update)

    def test_run_check_media_updates_with_unknown_post(self):
        self._isolate_linkedin_account()
        with patch(
            PATCH_ACCOUNT_LINKEDIN.format("_get_posts"),
            autospec=True,
            return_value=[{"id": "urn:li:share:not-imported-yet"}],
        ):
            self.SocialAccount._run_check_media_updates()
        self.assertTrue(self.SocialAccountLinkedin.need_update)

    def test_run_check_media_updates_with_outdated_statistics(self):
        self._isolate_linkedin_account()
        remote_ref = self.SocialPostAccountLinkedin.remote_ref
        self.SocialPostAccountLinkedin.write(
            {
                "click_count": 0,
                "like_count": 0,
                "comment_count": 0,
                "share_count": 0,
            }
        )
        with (
            patch(
                PATCH_ACCOUNT_LINKEDIN.format("_get_posts"),
                autospec=True,
                return_value=[{"id": remote_ref}],
            ),
            patch(
                PATCH_ACCOUNT_LINKEDIN.format("get_entity_statistics"),
                autospec=True,
                return_value={remote_ref: (0, 0, 0, 0, 0, 0)},
            ),
        ):
            self.SocialAccount._run_check_media_updates()
        self.assertFalse(self.SocialAccountLinkedin.need_update)
        with (
            patch(
                PATCH_ACCOUNT_LINKEDIN.format("_get_posts"),
                autospec=True,
                return_value=[{"id": remote_ref}],
            ),
            patch(
                PATCH_ACCOUNT_LINKEDIN.format("get_entity_statistics"),
                autospec=True,
                return_value={remote_ref: (1, 2, 3, 4, 5, 6)},
            ),
        ):
            self.SocialAccount._run_check_media_updates()
        self.assertTrue(self.SocialAccountLinkedin.need_update)

    @mute_logger(LOGGER_ACCOUNT_LINKEDIN)
    def test_run_check_media_updates_exception(self):
        self._isolate_linkedin_account()
        with patch(
            PATCH_ACCOUNT_LINKEDIN.format("_get_posts"),
            autospec=True,
            side_effect=Exception("Error Check Media Updates"),
        ):
            self.assertFalse(self.SocialAccount._run_check_media_updates())
        self.assertFalse(self.SocialAccountLinkedin.need_update)

    def test_campaign_archive_linkedin(self):
        campaign = self.SocialCampaignLinkedin
        campaign.account_id = self.SocialAccountLinkedin
        messages = len(campaign.message_ids)
        with self._mock_linkedin(
            MagicMock(status_code=204), self.SocialAccountLinkedin
        ) as mock_request:
            campaign.action_archive_linkedin()
        self.assertEqual(campaign.linkedin_status, "archived")
        self.assertFalse(campaign.linkedin_needs_update)
        self.assertEqual(len(campaign.message_ids), messages + 1)
        self.assertEqual(
            mock_request.call_args.kwargs["json_data"],
            {"patch": {"$set": {"status": "ARCHIVED"}}},
        )
        self.assertEqual(
            mock_request.call_args.kwargs["endpoint"], "/adCampaignsV2/001"
        )
        with self.assertRaises(
            UserError, msg="An archived campaign is read only on LinkedIn."
        ):
            campaign.action_archive_linkedin()

    def test_campaign_archive_linkedin_errors(self):
        campaign = self.UtmCampaign.create(
            {
                "name": "Campaign Without Urn",
                "campaign_group_id": self.SocialCampaignGroupLinkedin.id,
                "media_id": self.media_linkedin_id.id,
                "account_id": self.SocialAccountLinkedin.id,
            }
        )
        with self.assertRaises(UserError):
            campaign.action_archive_linkedin()
        campaign.write({"remote_ref": "urn:li:sponsoredCampaign:003"})
        campaign.account_id = False
        with self.assertRaises(UserError):
            campaign.action_archive_linkedin()
        campaign.account_id = self.SocialAccountLinkedin
        error_response = MagicMock(status_code=400)
        error_response.json.return_value = {"message": "Cannot archive"}
        with self._mock_linkedin(error_response, self.SocialAccountLinkedin):
            with self.assertRaises(UserError):
                campaign.action_archive_linkedin()
        self.assertNotEqual(campaign.linkedin_status, "archived")

    def test_group_archive_linkedin(self):
        group = self.SocialCampaignGroupLinkedin
        messages = len(group.message_ids)
        with self._mock_linkedin(
            MagicMock(status_code=204), self.SocialAccountLinkedin
        ) as mock_request:
            group.action_archive_linkedin()
        self.assertEqual(group.linkedin_status, "archived")
        self.assertFalse(group.linkedin_needs_update)
        self.assertEqual(len(group.message_ids), messages + 1)
        self.assertEqual(
            mock_request.call_args.kwargs["json_data"],
            {"patch": {"$set": {"status": "ARCHIVED"}}},
        )
        self.assertEqual(
            mock_request.call_args.kwargs["endpoint"], "/adCampaignGroupsV2/456"
        )
        with self.assertRaises(
            UserError, msg="An archived campaign group is read only on LinkedIn."
        ):
            group.action_archive_linkedin()

    def test_group_archive_linkedin_errors(self):
        group = self.UtmGroupCampaign.create(
            {
                "name": "Group Without Urn",
                "total_budget": 100,
                "currency_id": self.env.ref("base.USD").id,
            }
        )
        with self.assertRaises(UserError):
            group.action_archive_linkedin()
        group.write({"remote_ref": "urn:li:sponsoredCampaignGroup:457"})
        with (
            patch(
                "odoo.addons.social_media_linkedin.models.utm_group_campaign."
                "UtmGroupCampaign._get_linkedin_account",
                autospec=True,
                return_value=self.env["social.account"],
            ),
            self.assertRaises(UserError),
        ):
            group.action_archive_linkedin()
        error_response = MagicMock(status_code=400)
        error_response.json.return_value = {"message": "Cannot archive"}
        with self._mock_linkedin(error_response, self.SocialAccountLinkedin):
            with self.assertRaises(UserError):
                group.action_archive_linkedin()
        self.assertNotEqual(group.linkedin_status, "archived")
