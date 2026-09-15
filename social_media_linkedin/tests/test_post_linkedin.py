# Copyright 2026 Binhex <https://www.binhex.cloud>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import base64
from unittest.mock import MagicMock, patch
from urllib.parse import quote

from odoo import Command
from odoo.exceptions import UserError
from odoo.tests.common import tagged
from odoo.tools import mute_logger

from odoo.addons.social_media_base.exceptions import SocialCredentialsError
from odoo.addons.social_media_linkedin.social_linkedin_utils import (
    _BATCH_GET_MAX_IDS_LINKEDIN,
    _ENDPOINT_POST_LINKEDIN,
    _ENDPOINT_POSTS_LINKEDIN,
    _MAX_IMAGE_SIZE_LINKEDIN,
    _MAX_IMAGES_LINKEDIN,
    _MAX_MESSAGE_LENGTH_LINKEDIN,
)
from odoo.addons.social_media_linkedin.tests.test_common_linkedin import (
    PATCH_ACCOUNT_LINKEDIN,
    TestSocialCommonLinkedin,
)

LOGGER_POST_ACCOUNT_LINKEDIN = (
    "odoo.addons.social_media_linkedin.models.social_post_account"
)
LOGGER_POST_ACCOUNT_BASE = "odoo.addons.social_media_base.models.social_post_account"
LOGGER_ACCOUNT_LINKEDIN = "odoo.addons.social_media_linkedin.models.social_account"
MODULE_POST_LINKEDIN = "odoo.addons.social_media_linkedin.models.social_post"


@tagged("post_install", "-at_install")
class TestSocialPostLinkedin(TestSocialCommonLinkedin):
    def test_post_check_messages(self):
        post_message_info = self.SocialPost.create(
            {
                "message": self.test_message,
                "account_ids": [Command.set(self.SocialAccountLinkedin.ids)],
                "image_ids": [Command.set([self.create_attachment().id])],
                "video_ids": [
                    Command.set([self.create_attachment("test_video.mp4").id])
                ],
            }
        )
        self.assertTrue(post_message_info.message_info)
        self.assertIn(
            "LinkedIn does not combine images and a video",
            post_message_info.message_info,
        )

        post = self.SocialPost.create(
            {
                "message": self.test_message,
                "account_ids": [Command.set(self.SocialAccountLinkedin.ids)],
                "image_ids": [Command.set([self.create_attachment().id])],
            }
        )
        self.assertFalse(post.message_info)

    def test_post_check_messages_recomputed_on_media_change(self):
        post = self.SocialPost.create(
            {
                "message": self.test_message,
                "account_ids": [Command.set(self.SocialAccountLinkedin.ids)],
                "image_ids": [Command.set([self.create_attachment().id])],
            }
        )
        self.assertFalse(post.message_info)

        post.video_ids = [Command.set([self.create_attachment("test_video.mp4").id])]
        self.assertIn(
            "LinkedIn does not combine images and a video",
            post.message_info,
        )

        post.image_ids = [Command.clear()]
        self.assertFalse(post.message_info)

    def test_post_check_messages_video_wins_over_the_images(self):
        """The warning must say what the connector really publishes."""
        post = self.SocialPost.create(
            {
                "message": self.test_message,
                "account_ids": [Command.set(self.SocialAccountLinkedin.ids)],
                "image_ids": [Command.set([self.create_attachment().id])],
                "video_ids": [
                    Command.set([self.create_attachment("test_video.mp4").id])
                ],
            }
        )
        self.assertIn("only the video will be published", post.message_info)

    def test_post_preview_video_wins_over_the_images(self):
        """The preview must show what LinkedIn publishes, not the rest."""
        image = self.create_attachment("preview_image.jpg")
        video = self.create_attachment("preview_video.mp4")
        post = self.SocialPost.create(
            {
                "message": self.test_message,
                "account_ids": [Command.set(self.SocialAccountLinkedin.ids)],
                "image_ids": [Command.set([image.id])],
                "video_ids": [Command.set([video.id])],
            }
        )
        self.assertNotIn(f"/web/image/{image.id}", post.post_preview)
        self.assertIn("preview_video.mp4", post.post_preview)

    def test_post_preview_keeps_the_images_without_a_video(self):
        image = self.create_attachment("preview_image.jpg")
        post = self.SocialPost.create(
            {
                "message": self.test_message,
                "account_ids": [Command.set(self.SocialAccountLinkedin.ids)],
                "image_ids": [Command.set([image.id])],
            }
        )
        self.assertIn(f"/web/image/{image.id}", post.post_preview)

    def test_post_schedule(self):
        post_hide = self.SocialPost.create(
            {
                "message": self.test_message,
                "send_post": "schedule",
                "account_ids": [Command.set(self.SocialAccountLinkedin.ids)],
            }
        )
        self.assertEqual(post_hide.state, "planned")
        self.assertFalse(post_hide.hide_post)
        post_hide.action_draft()
        self.assertEqual(post_hide.state, "draft")
        self.assertFalse(post_hide.hide_post)
        post_hide.send_post = "schedule"
        post_hide.action_cancel()
        self.assertEqual(post_hide.state, "cancelled")

    @patch(PATCH_ACCOUNT_LINKEDIN.format("_request_linkedin"))
    def test_delete_post_account(self, mock_request_linkedin):
        mock_response = MagicMock()
        mock_response.status_code = 204
        mock_request_linkedin.return_value = mock_response
        self.SocialPostAccountLinkedin._delete_post_account()

        mock_failed_response = MagicMock()
        mock_failed_response.status_code = 404
        mock_request_linkedin.return_value = mock_failed_response
        with self.assertRaises(UserError):
            self.SocialPostAccountLinkedin._delete_post_account()
        self.assertEqual(mock_request_linkedin.call_count, 2)

    @patch(PATCH_ACCOUNT_LINKEDIN.format("_request_linkedin"))
    def test_delete_post_account_refreshes_the_token_first(self, mock_request_linkedin):
        """A 401 here would be reported as an undeletable post."""
        mock_request_linkedin.return_value = MagicMock(status_code=204)
        with patch.object(
            type(self.SocialAccount), "validate_access_token", autospec=True
        ) as mock_validate:
            self.SocialPostAccountLinkedin._delete_post_account()
        mock_validate.assert_called_once()
        self.assertTrue(
            mock_validate.call_args.args[0].env.context.get("not_notify"),
            msg="Deleting a publication must not report that the token is valid.",
        )

    def test_action_post(self):
        self.SocialPostAccountLinkedin.write({"state": "ready"})
        post_account_urn = "urn:li:share:122809890045"
        fake_response = [
            {
                "id": post_account_urn,
                "content": {"media": {"id": "urn:li:image:1"}},
            }
        ]
        with patch.object(
            type(self.SocialPostLinkedin),
            "_filter_by_media_types",
            autospec=True,
            return_value=self.SocialPostAccountLinkedin,
        ) as mock_filter_by_media_types, patch.object(
            type(self.SocialPostAccountLinkedin.account_id),
            "_linkedin_create_post",
            autospec=True,
            return_value=(post_account_urn, {}),
        ) as mock_linkedin_create_post, patch.object(
            type(self.SocialPostAccountLinkedin.account_id),
            "_get_posts",
            autospec=True,
            return_value=fake_response,
        ) as mock_get_posts:
            self.SocialPostAccountLinkedin._action_post(self.SocialPostLinkedin)
            self.assertEqual(
                self.SocialPostAccountLinkedin.remote_ref,
                post_account_urn,
            )
            self.assertEqual(self.SocialPostAccountLinkedin.state, "posted")
            self.assertFalse(self.SocialPostAccountLinkedin.has_video)
            self.assertEqual(
                self.SocialPostAccountLinkedin.post_account_url,
                f"https://www.linkedin.com/feed/update/{post_account_urn}",
            )
            mock_filter_by_media_types.assert_called_once()
            mock_linkedin_create_post.assert_called_once()
            mock_get_posts.assert_not_called()

    def test_action_post_video_sets_has_video(self):
        self.SocialPostAccountLinkedin.write({"state": "ready", "remote_ref": False})
        self.SocialPostLinkedin.write(
            {"video_ids": [Command.set([self.create_attachment("test_video.mp4").id])]}
        )
        post_account_urn = "urn:li:ugcPost:122809890045"
        fake_response = [
            {
                "id": post_account_urn,
                "content": {"media": {"id": "urn:li:image:1"}},
            }
        ]
        with patch.object(
            type(self.SocialPostLinkedin),
            "_filter_by_media_types",
            autospec=True,
            return_value=self.SocialPostAccountLinkedin,
        ), patch.object(
            type(self.SocialPostAccountLinkedin.account_id),
            "_linkedin_create_post",
            autospec=True,
            return_value=(post_account_urn, {}),
        ), patch.object(
            type(self.SocialPostAccountLinkedin.account_id),
            "_get_posts",
            autospec=True,
            return_value=fake_response,
        ):
            self.SocialPostAccountLinkedin._action_post(self.SocialPostLinkedin)
        self.assertEqual(self.SocialPostAccountLinkedin.state, "posted")
        self.assertTrue(self.SocialPostAccountLinkedin.has_video)

    def test_action_post_images_and_video_is_a_warning_and_publishes(self):
        """Only the video goes out, which is the post published, not refused."""
        self.SocialPostAccountLinkedin.write({"state": "ready", "remote_ref": False})
        self.SocialPostLinkedin.write(
            {
                "image_ids": [Command.set([self.create_attachment("one.jpg").id])],
                "video_ids": [Command.set([self.create_attachment("clip.mp4").id])],
            }
        )
        self.assertFalse(self.SocialPostLinkedin.message_error)
        self.assertIn(
            "only the video will be published", self.SocialPostLinkedin.message_info
        )
        post_account_urn = "urn:li:ugcPost:122809890099"
        with patch.object(
            type(self.SocialPostLinkedin),
            "_filter_by_media_types",
            autospec=True,
            return_value=self.SocialPostAccountLinkedin,
        ), patch.object(
            type(self.SocialPostAccountLinkedin.account_id),
            "_linkedin_create_post",
            autospec=True,
            return_value=(post_account_urn, {}),
        ), patch.object(
            type(self.SocialPostAccountLinkedin.account_id),
            "_get_posts",
            autospec=True,
            return_value=[],
        ):
            self.SocialPostAccountLinkedin._action_post(self.SocialPostLinkedin)
        self.assertEqual(self.SocialPostAccountLinkedin.state, "posted")
        self.assertEqual(self.SocialPostAccountLinkedin.remote_ref, post_account_urn)

    @mute_logger(LOGGER_POST_ACCOUNT_BASE)
    def test_action_post_with_several_videos_is_refused(self):
        """The check runs before uploading anything to LinkedIn."""
        self.SocialPostAccountLinkedin.write({"state": "ready", "remote_ref": False})
        self.SocialPostLinkedin.write(
            {
                "video_ids": [
                    Command.set(
                        [
                            self.create_attachment("one.mp4").id,
                            self.create_attachment("two.mp4").id,
                        ]
                    )
                ]
            }
        )
        with patch.object(
            type(self.SocialPostLinkedin),
            "_filter_by_media_types",
            autospec=True,
            return_value=self.SocialPostAccountLinkedin,
        ), patch.object(
            type(self.SocialPostAccountLinkedin.account_id),
            "_linkedin_prepare_videos_for_post",
            autospec=True,
        ) as mock_prepare_videos, patch.object(
            type(self.SocialPostAccountLinkedin.account_id),
            "_linkedin_create_post",
            autospec=True,
        ) as mock_linkedin_create_post:
            self.SocialPostAccountLinkedin._action_post(self.SocialPostLinkedin)
            mock_prepare_videos.assert_not_called()
            mock_linkedin_create_post.assert_not_called()
        self.assertEqual(self.SocialPostAccountLinkedin.state, "failed")
        self.assertIn(
            "single video per post", self.SocialPostAccountLinkedin.failed_description
        )

    def test_check_publishable_accepts_a_gif(self):
        """The Images API takes GIF, so nothing may refuse it here."""
        self.SocialPostAccountLinkedin.write({"state": "ready", "remote_ref": False})
        self.SocialPostLinkedin.write(
            {"image_ids": [Command.set([self.create_attachment("animation.gif").id])]}
        )
        self.SocialPostAccountLinkedin._check_publishable()
        self.assertNotIn("GIF", self.SocialPostLinkedin.message_error or "")

    def test_check_publishable_rejects_a_mov_video(self):
        """The Videos API only takes MP4, whatever the file dialog let through."""
        self.SocialPostAccountLinkedin.write({"state": "ready", "remote_ref": False})
        self.SocialPostLinkedin.write(
            {"video_ids": [Command.set([self.create_attachment("holidays.mov").id])]}
        )
        with self.assertRaises(UserError):
            self.SocialPostAccountLinkedin._check_publishable()
        self.assertIn("MP4 videos", self.SocialPostLinkedin.message_error)

    def test_check_publishable_ignores_the_images_when_there_is_a_video(self):
        """A video drops the images, so their format decides nothing."""
        self.SocialPostAccountLinkedin.write({"state": "ready", "remote_ref": False})
        self.SocialPostLinkedin.write(
            {
                "image_ids": [Command.set([self.create_attachment("picture.webp").id])],
                "video_ids": [Command.set([self.create_attachment("clip.mp4").id])],
            }
        )
        self.SocialPostAccountLinkedin._check_publishable()
        self.assertNotIn(
            "JPG, PNG and GIF", self.SocialPostLinkedin.message_error or ""
        )

    def test_check_publishable_rejects_an_unsupported_image(self):
        self.SocialPostAccountLinkedin.write({"state": "ready", "remote_ref": False})
        self.SocialPostLinkedin.write(
            {"image_ids": [Command.set([self.create_attachment("picture.webp").id])]}
        )
        with self.assertRaises(UserError):
            self.SocialPostAccountLinkedin._check_publishable()
        self.assertIn("JPG, PNG and GIF", self.SocialPostLinkedin.message_error)

    def test_action_post_fails_only_the_line_with_the_wrong_format(self):
        """The format is checked before anything is uploaded to LinkedIn."""
        self.SocialPostAccountLinkedin.write({"state": "ready", "remote_ref": False})
        self.SocialPostLinkedin.write(
            {"video_ids": [Command.set([self.create_attachment("holidays.mov").id])]}
        )
        with patch.object(
            type(self.SocialPostLinkedin),
            "_filter_by_media_types",
            autospec=True,
            return_value=self.SocialPostAccountLinkedin,
        ), patch.object(
            type(self.SocialPostAccountLinkedin.account_id),
            "_linkedin_create_post",
            autospec=True,
        ) as mock_linkedin_create_post:
            self.SocialPostAccountLinkedin._action_post(self.SocialPostLinkedin)
            mock_linkedin_create_post.assert_not_called()
        self.assertEqual(self.SocialPostAccountLinkedin.state, "failed")
        self.assertIn("MP4 videos", self.SocialPostAccountLinkedin.failed_description)
        self.assertIn(
            self.SocialPostLinkedin.message_error,
            self.SocialPostAccountLinkedin.failed_description,
            msg="The publication and the form must not word the refusal apart.",
        )

    def test_action_post_keeps_the_upload_order_of_the_images(self):
        """LinkedIn draws the images in the order it receives them."""
        self.SocialPostAccountLinkedin.write({"state": "ready", "remote_ref": False})
        images = self.env["ir.attachment"].create(
            [
                {
                    "name": f"image_{number}.jpg",
                    "type": "binary",
                    "datas": self.VALID_PNG_B64,
                }
                for number in range(3)
            ]
        )
        self.SocialPostLinkedin.write({"image_ids": [Command.set(images.ids)]})
        # Read back from database: a many2many follows the ``id desc`` order
        # of ``ir.attachment``, which is the order the cron would publish.
        self.SocialPostLinkedin.invalidate_recordset()
        with patch.object(
            type(self.SocialPostLinkedin),
            "_filter_by_media_types",
            autospec=True,
            return_value=self.SocialPostAccountLinkedin,
        ), patch.object(
            type(self.SocialPostAccountLinkedin.account_id),
            "_linkedin_create_post",
            autospec=True,
            return_value=("urn:li:share:1", {}),
        ) as mock_linkedin_create_post, patch.object(
            type(self.SocialPostAccountLinkedin),
            "_linkedin_enrich_published_post",
            autospec=True,
        ):
            self.SocialPostAccountLinkedin._action_post(self.SocialPostLinkedin)
        self.assertEqual(
            list(mock_linkedin_create_post.call_args.kwargs["image_ids"].ids),
            images.ids,
        )

    def _draft_post(self, **values):
        """Create a LinkedIn post that nothing has published yet.

        The post of the common setup already carries a publication with its
        remote reference, so its content is locked and cannot be written on.
        """
        return self.SocialPost.create(
            dict(
                {
                    "message": self.test_message,
                    "account_ids": [Command.set(self.SocialAccountLinkedin.ids)],
                },
                **values,
            )
        )

    def test_get_post_errors_calls_super(self):
        """The connector adds to what the other modules already refused."""
        post = self._draft_post()
        parent_cls = self._get_parent_class_defining(post, "_get_post_errors")
        with patch.object(
            parent_cls,
            "_get_post_errors",
            autospec=True,
            return_value=["Refused by another module"],
        ) as mock_super:
            errors = post._get_post_errors("linkedin")
        self.assertEqual(errors, ["Refused by another module"])
        mock_super.assert_called_once()

    def test_get_post_warnings_calls_super(self):
        """The connector adds to what the other modules already said."""
        post = self._draft_post()
        parent_cls = self._get_parent_class_defining(post, "_get_post_warnings")
        with patch.object(
            parent_cls,
            "_get_post_warnings",
            autospec=True,
            return_value=["Changed by another module"],
        ) as mock_super:
            warnings = post._get_post_warnings("linkedin")
        self.assertEqual(warnings, ["Changed by another module"])
        mock_super.assert_called_once()

    def test_get_post_errors_leaves_the_other_media_alone(self):
        """A rule of LinkedIn says nothing about a post published elsewhere."""
        post = self._draft_post(message="x" * (_MAX_MESSAGE_LENGTH_LINKEDIN + 1))
        self.assertFalse(post._get_post_errors("x"))

    def test_get_post_errors_message_too_long(self):
        post = self._draft_post(message="x" * (_MAX_MESSAGE_LENGTH_LINKEDIN + 1))
        self.assertIn(
            "at most 3000 characters", "\n".join(post._get_post_errors("linkedin"))
        )

    def test_get_post_errors_too_many_images(self):
        post = self._draft_post(
            image_ids=[
                Command.set(
                    [
                        self.create_attachment(f"image_{number}.jpg").id
                        for number in range(_MAX_IMAGES_LINKEDIN + 1)
                    ]
                )
            ]
        )
        self.assertIn("at most 20 images", "\n".join(post._get_post_errors("linkedin")))

    def test_get_post_errors_image_too_large(self):
        image = self.create_attachment("picture.jpg", size=_MAX_IMAGE_SIZE_LINKEDIN + 1)
        post = self._draft_post(image_ids=[Command.set(image.ids)])
        self.assertIn("images of at most", "\n".join(post._get_post_errors("linkedin")))

    def test_get_post_errors_video_too_large(self):
        """The limit is lowered instead of building the 500 MB it stops at."""
        video = self.create_attachment("clip.mp4", size=1024)
        post = self._draft_post(video_ids=[Command.set(video.ids)])
        self.assertFalse(post._get_post_errors("linkedin"))
        with patch(MODULE_POST_LINKEDIN + "._MAX_VIDEO_SIZE_LINKEDIN", 512):
            self.assertIn(
                "videos of at most", "\n".join(post._get_post_errors("linkedin"))
            )

    def test_get_post_errors_a_video_drops_every_image_rule(self):
        """With a video the images are not published, so nothing about them counts."""
        post = self._draft_post(
            image_ids=[
                Command.set(
                    [
                        self.create_attachment(
                            "picture.webp", size=_MAX_IMAGE_SIZE_LINKEDIN + 1
                        ).id
                    ]
                    + [
                        self.create_attachment(f"image_{number}.jpg").id
                        for number in range(_MAX_IMAGES_LINKEDIN)
                    ]
                )
            ],
            video_ids=[Command.set([self.create_attachment("clip.mp4").id])],
        )
        self.assertFalse(post._get_post_errors("linkedin"))
        self.assertIn(
            "only the video will be published",
            "\n".join(post._get_post_warnings("linkedin")),
        )

    def test_post_check_messages_several_videos(self):
        post = self.SocialPost.create(
            {
                "message": self.test_message,
                "account_ids": [Command.set(self.SocialAccountLinkedin.ids)],
                "video_ids": [
                    Command.set(
                        [
                            self.create_attachment("one.mp4").id,
                            self.create_attachment("two.mp4").id,
                        ]
                    )
                ],
            }
        )
        self.assertIn("single video per post", post.message_error)

    @mute_logger(LOGGER_POST_ACCOUNT_BASE)
    def test_action_post_isolates_the_failing_account(self):
        """One account failing must not undo the one that did publish."""
        post_account_urn = "urn:li:share:122809890046"
        second_account = self.SocialAccountLinkedin.copy(
            {"name": "Second LinkedIn account", "remote_ref": "urn:li:organization:2"}
        )
        second_post_account = self.SocialPostAccountLinkedin.copy(
            {"account_id": second_account.id, "state": "ready", "remote_ref": False}
        )
        self.SocialPostAccountLinkedin.write({"state": "ready", "remote_ref": False})
        post_accounts = self.SocialPostAccountLinkedin | second_post_account
        with patch.object(
            type(self.SocialPostLinkedin),
            "_filter_by_media_types",
            autospec=True,
            return_value=post_accounts,
        ), patch.object(
            type(self.SocialPostAccountLinkedin.account_id),
            "_linkedin_create_post",
            autospec=True,
            side_effect=[
                (post_account_urn, []),
                UserError("LinkedIn refused the post"),
            ],
        ), patch.object(
            type(self.SocialPostAccountLinkedin.account_id),
            "_get_posts",
            autospec=True,
            return_value=[],
        ):
            self.SocialPostAccountLinkedin._action_post(self.SocialPostLinkedin)
        self.assertEqual(self.SocialPostAccountLinkedin.state, "posted")
        self.assertEqual(self.SocialPostAccountLinkedin.remote_ref, post_account_urn)
        self.assertEqual(second_post_account.state, "failed")
        self.assertIn(
            "LinkedIn refused the post", second_post_account.failed_description
        )
        self.assertFalse(second_post_account.remote_ref)

    @mute_logger(LOGGER_POST_ACCOUNT_BASE)
    def test_check_publishable_fails_only_its_own_line(self):
        """A publication refused by the generic check stops that one alone."""
        post_account_urn = "urn:li:share:122809890060"
        second_account = self.SocialAccountLinkedin.copy(
            {"name": "Second LinkedIn account", "remote_ref": "urn:li:organization:3"}
        )
        second_post_account = self.SocialPostAccountLinkedin.copy(
            {"account_id": second_account.id, "state": "ready", "remote_ref": False}
        )
        self.SocialPostAccountLinkedin.write({"state": "ready", "remote_ref": False})
        post_accounts = self.SocialPostAccountLinkedin | second_post_account
        refusal = "The extension refused this publication"

        def refuse_the_second(post_account):
            if post_account == second_post_account:
                raise UserError(refusal)

        with patch.object(
            type(self.SocialPostLinkedin),
            "_filter_by_media_types",
            autospec=True,
            return_value=post_accounts,
        ), patch.object(
            type(self.SocialPostAccountLinkedin),
            "_check_publishable",
            autospec=True,
            side_effect=refuse_the_second,
        ), patch.object(
            type(self.SocialPostAccountLinkedin.account_id),
            "_linkedin_create_post",
            autospec=True,
            return_value=(post_account_urn, {}),
        ), patch.object(
            type(self.SocialPostAccountLinkedin.account_id),
            "_get_posts",
            autospec=True,
            return_value=[],
        ):
            self.SocialPostAccountLinkedin._action_post(self.SocialPostLinkedin)
        self.assertEqual(self.SocialPostAccountLinkedin.state, "posted")
        self.assertEqual(self.SocialPostAccountLinkedin.remote_ref, post_account_urn)
        self.assertEqual(second_post_account.state, "failed")
        self.assertFalse(second_post_account.remote_ref)
        self.assertIn(refusal, second_post_account.failed_description)

    def test_linkedin_published_values_are_written(self):
        """What the extension point returns is stored with the publication."""
        post_account_urn = "urn:li:share:122809890061"
        self.SocialPostAccountLinkedin.write({"state": "ready", "remote_ref": False})
        with patch.object(
            type(self.SocialPostLinkedin),
            "_filter_by_media_types",
            autospec=True,
            return_value=self.SocialPostAccountLinkedin,
        ), patch.object(
            type(self.SocialPostAccountLinkedin),
            "_linkedin_published_values",
            autospec=True,
            return_value={"message": "Written by the extension"},
        ), patch.object(
            type(self.SocialPostAccountLinkedin.account_id),
            "_linkedin_create_post",
            autospec=True,
            return_value=(post_account_urn, {}),
        ), patch.object(
            type(self.SocialPostAccountLinkedin.account_id),
            "_get_posts",
            autospec=True,
            return_value=[],
        ):
            self.SocialPostAccountLinkedin._action_post(self.SocialPostLinkedin)
        self.assertEqual(self.SocialPostAccountLinkedin.remote_ref, post_account_urn)
        self.assertEqual(
            self.SocialPostAccountLinkedin.message, "Written by the extension"
        )

    @mute_logger(LOGGER_POST_ACCOUNT_LINKEDIN)
    def test_linkedin_published_values_failing_keeps_the_publication(self):
        """An error of the extension point never undoes a published post.

        _linkedin_published_values runs inside the try of
        :meth:`_linkedin_enrich_published_post`, so its failure is logged and
        the remote reference of a post that is already online survives.
        """
        post_account_urn = "urn:li:share:122809890062"
        self.SocialPostAccountLinkedin.write({"state": "ready", "remote_ref": False})
        with patch.object(
            type(self.SocialPostLinkedin),
            "_filter_by_media_types",
            autospec=True,
            return_value=self.SocialPostAccountLinkedin,
        ), patch.object(
            type(self.SocialPostAccountLinkedin),
            "_linkedin_published_values",
            autospec=True,
            side_effect=ValueError("The extension broke"),
        ), patch.object(
            type(self.SocialPostAccountLinkedin.account_id),
            "_linkedin_create_post",
            autospec=True,
            return_value=(post_account_urn, {}),
        ):
            self.SocialPostAccountLinkedin._action_post(self.SocialPostLinkedin)
        self.assertEqual(self.SocialPostAccountLinkedin.state, "posted")
        self.assertEqual(self.SocialPostAccountLinkedin.remote_ref, post_account_urn)

    def test_action_post_does_not_ask_linkedin_for_the_post_it_just_created(self):
        """Publishing costs one call: the medias are already known."""
        image = self.create_attachment("published.jpg")
        self.SocialPostAccountLinkedin.write({"state": "ready", "remote_ref": False})
        self.SocialPostLinkedin.write({"image_ids": [Command.set(image.ids)]})
        with patch.object(
            type(self.SocialPostLinkedin),
            "_filter_by_media_types",
            autospec=True,
            return_value=self.SocialPostAccountLinkedin,
        ), patch.object(
            type(self.SocialPostAccountLinkedin.account_id),
            "_linkedin_create_post",
            autospec=True,
            return_value=("urn:li:share:once", {str(image.id): "urn:li:image:once"}),
        ), patch.object(
            type(self.SocialPostAccountLinkedin.account_id),
            "_get_posts",
            autospec=True,
        ) as mock_get_posts:
            self.SocialPostAccountLinkedin._action_post(self.SocialPostLinkedin)
        mock_get_posts.assert_not_called()

    def test_action_post_publishes_the_images_in_the_order_they_were_added(self):
        """LinkedIn receives the images in the order the user uploaded them.

        ``ir.attachment`` reads back newest first, so what is published would
        be reversed without :meth:`_sorted_medias`.
        """
        images = self.env["ir.attachment"].create(
            [
                {
                    "name": f"ordered_{index}.jpg",
                    "type": "binary",
                    "datas": base64.b64encode(f"image {index}".encode()).decode(),
                }
                for index in range(3)
            ]
        )
        self.SocialPostAccountLinkedin.write({"state": "ready", "remote_ref": False})
        self.SocialPostLinkedin.write({"image_ids": [Command.set(images.ids)]})
        with patch.object(
            type(self.SocialPostLinkedin),
            "_filter_by_media_types",
            autospec=True,
            return_value=self.SocialPostAccountLinkedin,
        ), patch.object(
            type(self.SocialPostAccountLinkedin.account_id),
            "_linkedin_create_post",
            autospec=True,
            return_value=("urn:li:share:ordered", {}),
        ) as mock_create_post:
            self.SocialPostAccountLinkedin._action_post(self.SocialPostLinkedin)
        self.assertEqual(
            mock_create_post.call_args.kwargs["image_ids"].ids,
            images.ids,
            "The connector must publish the medias oldest first, which is the "
            "order the gallery and the preview draw them in",
        )

    def test_action_post_renews_the_token_and_publishes_again(self):
        """A token refused at the last moment is renewed and the post goes out."""
        post_account_urn = "urn:li:share:122809890050"
        self.SocialPostAccountLinkedin.write({"state": "ready", "remote_ref": False})
        with patch.object(
            type(self.SocialPostLinkedin),
            "_filter_by_media_types",
            autospec=True,
            return_value=self.SocialPostAccountLinkedin,
        ), patch.object(
            type(self.SocialPostAccountLinkedin.account_id),
            "_linkedin_create_post",
            autospec=True,
            side_effect=[
                SocialCredentialsError("The access token expired"),
                (post_account_urn, []),
            ],
        ) as mock_create_post, patch.object(
            type(self.SocialPostAccountLinkedin.account_id),
            "_refresh_credentials",
            autospec=True,
            return_value=True,
        ) as mock_refresh, patch.object(
            type(self.SocialPostAccountLinkedin.account_id),
            "_get_posts",
            autospec=True,
            return_value=[],
        ):
            self.SocialPostAccountLinkedin._action_post(self.SocialPostLinkedin)
        mock_refresh.assert_called_once()
        self.assertEqual(mock_create_post.call_count, 2)
        self.assertEqual(self.SocialPostAccountLinkedin.state, "posted")
        self.assertEqual(self.SocialPostAccountLinkedin.remote_ref, post_account_urn)

    @mute_logger(LOGGER_POST_ACCOUNT_BASE)
    def test_action_post_without_token_says_so_on_the_line(self):
        """A publication skipped for lack of token must explain itself."""
        self.SocialPostAccountLinkedin.write({"state": "ready", "remote_ref": False})
        self.SocialAccountLinkedin.sudo().access_token = False
        with patch.object(
            type(self.SocialPostLinkedin),
            "_filter_by_media_types",
            autospec=True,
            return_value=self.SocialPostAccountLinkedin,
        ):
            self.SocialPostAccountLinkedin._action_post(self.SocialPostLinkedin)
        self.assertEqual(self.SocialPostAccountLinkedin.state, "failed")
        self.assertIn(
            "no LinkedIn access token",
            self.SocialPostAccountLinkedin.failed_description,
        )
        self.assertTrue(self.SocialAccountLinkedin.need_update)

    def test_action_post_writes_a_media_ref_per_account(self):
        """The same image gives a different reference on each account."""
        image = self.env["ir.attachment"].create(
            {
                "name": "shared.jpg",
                "type": "binary",
                "datas": base64.b64encode(b"shared image").decode(),
            }
        )
        accounts = self.SocialAccountLinkedin | self.SocialAccountLinkedinData
        post = self.SocialPost.create(
            {
                "message": "Two accounts, one image",
                "account_ids": [Command.set(accounts.ids)],
                "image_ids": [Command.set(image.ids)],
            }
        )
        lines = self.SocialPostAccount.create(
            [
                {
                    "message": post.message,
                    "account_id": account.id,
                    "post_id": post.id,
                    "state": "ready",
                    # What the fan-out does: every publication points at the
                    # very attachments of the post.
                    "image_ids": [Command.set(image.ids)],
                }
                for account in accounts
            ]
        )
        urns = iter(["urn:li:image:A", "urn:li:image:B"])

        def _create_post(account, message=None, image_ids=None, video_ids=None):
            return f"urn:li:share:{account.id}", {str(image.id): next(urns)}

        with patch.object(
            type(post),
            "_filter_by_media_types",
            autospec=True,
            return_value=lines,
        ), patch.object(
            type(self.SocialAccountLinkedin),
            "_linkedin_create_post",
            autospec=True,
            side_effect=_create_post,
        ), patch.object(
            type(lines),
            "_linkedin_enrich_published_post",
            autospec=True,
        ):
            lines._action_post(post)
        lines.invalidate_recordset(["media_refs"])
        self.assertEqual(
            [line.media_refs for line in lines],
            [
                {str(image.id): "urn:li:image:A"},
                {str(image.id): "urn:li:image:B"},
            ],
            "Two publications of one post point at the same attachment with "
            "the reference it got on each account",
        )

    def test_action_post_stores_the_video_reference(self):
        """The URN of the video is kept, and the card says there is one."""
        video = self.create_attachment("published_video.mp4")
        self.SocialPostAccountLinkedin.write(
            {
                "state": "ready",
                "remote_ref": False,
                # What the fan-out does: the publication points at the very
                # video of the post.
                "video_ids": [Command.set(video.ids)],
            }
        )
        self.SocialPostLinkedin.write({"video_ids": [Command.set(video.ids)]})
        with patch.object(
            type(self.SocialPostLinkedin),
            "_filter_by_media_types",
            autospec=True,
            return_value=self.SocialPostAccountLinkedin,
        ), patch.object(
            type(self.SocialPostAccountLinkedin.account_id),
            "_linkedin_create_post",
            autospec=True,
            return_value=("urn:li:share:video", {str(video.id): "urn:li:video:1"}),
        ), patch.object(
            type(self.SocialPostAccountLinkedin),
            "_linkedin_enrich_published_post",
            autospec=True,
        ):
            self.SocialPostAccountLinkedin._action_post(self.SocialPostLinkedin)
        self.SocialPostAccountLinkedin.invalidate_recordset(["media_refs"])
        self.assertEqual(
            self.SocialPostAccountLinkedin.media_refs,
            {str(video.id): "urn:li:video:1"},
        )
        self.assertTrue(self.SocialPostAccountLinkedin.has_video)

    def test_action_post_does_not_empty_the_images_on_a_retry(self):
        """Republishing a failed line must not clear what it already had."""
        post_account_urn = "urn:li:share:122809890050"
        stored = self.create_attachment(attach_name="urn:li:image:stored")
        self.SocialPostAccountLinkedin.write(
            {
                "state": "failed",
                "remote_ref": False,
                "image_ids": [Command.set(stored.ids)],
            }
        )
        with patch.object(
            type(self.SocialPostLinkedin),
            "_filter_by_media_types",
            autospec=True,
            return_value=self.SocialPostAccountLinkedin,
        ), patch.object(
            type(self.SocialPostAccountLinkedin.account_id),
            "_linkedin_create_post",
            autospec=True,
            return_value=(post_account_urn, {}),
        ), patch.object(
            type(self.SocialPostAccountLinkedin.account_id),
            "_get_posts",
            autospec=True,
            return_value=[],
        ):
            self.SocialPostAccountLinkedin._action_post(self.SocialPostLinkedin)
        self.assertEqual(self.SocialPostAccountLinkedin.state, "posted")
        self.assertEqual(self.SocialPostAccountLinkedin.image_ids, stored)

    @mute_logger(LOGGER_POST_ACCOUNT_LINKEDIN)
    def test_action_post_keeps_remote_ref_when_the_medias_fail(self):
        """The enrichment is best-effort: it never reverts a published post."""
        post_account_urn = "urn:li:share:122809890047"
        self.SocialPostAccountLinkedin.write({"state": "ready", "remote_ref": False})
        with patch.object(
            type(self.SocialPostLinkedin),
            "_filter_by_media_types",
            autospec=True,
            return_value=self.SocialPostAccountLinkedin,
        ), patch.object(
            type(self.SocialPostAccountLinkedin.account_id),
            "_linkedin_create_post",
            autospec=True,
            return_value=(post_account_urn, {}),
        ), patch.object(
            type(self.SocialPostAccountLinkedin.account_id),
            "_get_posts",
            autospec=True,
            side_effect=UserError("LinkedIn is not available"),
        ):
            self.SocialPostAccountLinkedin._action_post(self.SocialPostLinkedin)
        self.assertEqual(self.SocialPostAccountLinkedin.state, "posted")
        self.assertEqual(self.SocialPostAccountLinkedin.remote_ref, post_account_urn)

    def test_action_post_failed(self):
        self.SocialPostAccountLinkedin.write({"state": "ready"})
        with patch.object(
            type(self.SocialPostLinkedin),
            "_filter_by_media_types",
            autospec=True,
            return_value=self.SocialPostAccountLinkedin,
        ) as mock_filter_by_media_types, patch.object(
            type(self.SocialPostAccountLinkedin.account_id),
            "_linkedin_create_post",
            autospec=True,
            return_value=(False, {}),
        ) as mock_linkedin_create_post:
            self.SocialPostAccountLinkedin._action_post(self.SocialPostLinkedin)
            self.assertEqual(self.SocialPostAccountLinkedin.state, "failed")
            mock_filter_by_media_types.assert_called_once()
            mock_linkedin_create_post.assert_called_once()

    def test_default_account_ids_only_the_active_company(self):
        """An account of another allowed company is not preselected."""
        company = self.env["res.company"].create({"name": "Other Company"})
        other_account = self.SocialAccountLinkedin.copy({"company_id": company.id})
        self.assertNotIn(other_account.id, self.SocialPost._default_account_ids())
        self.assertIn(
            other_account.id,
            self.SocialPost.with_company(company)._default_account_ids(),
        )

    @patch(PATCH_ACCOUNT_LINKEDIN.format("_request_linkedin"))
    def test_check_remote_post_exists(self, mock_request):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_request.return_value = mock_response
        self.assertTrue(self.SocialPostAccountLinkedin.check_post_exists())

    @patch(PATCH_ACCOUNT_LINKEDIN.format("_request_linkedin"))
    def test_check_remote_post_exists_deleted(self, mock_request):
        """A 404 is the only answer that means the post is gone."""
        remote_ref = self.SocialPostAccountLinkedin.remote_ref
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_request.return_value = mock_response
        self.assertFalse(self.SocialPostAccountLinkedin.check_post_exists())
        self.assertEqual(self.SocialPostAccountLinkedin.state, "deleted")
        self.assertFalse(self.SocialPostAccountLinkedin.post_account_url)
        self.assertEqual(self.SocialPostAccountLinkedin.remote_ref, remote_ref)

    @patch(PATCH_ACCOUNT_LINKEDIN.format("_request_linkedin"))
    def test_check_remote_post_exists_forbidden(self, mock_request):
        """A lost permission is not a deletion: nothing may be written."""
        post_account = self.SocialPostAccountLinkedin
        post_account.write({"state": "posted"})
        remote_ref = post_account.remote_ref
        post_account_url = post_account.post_account_url
        mock_response = MagicMock()
        mock_response.status_code = 403
        mock_request.return_value = mock_response
        with mute_logger(LOGGER_POST_ACCOUNT_LINKEDIN):
            self.assertTrue(post_account.check_post_exists())
        self.assertEqual(post_account.state, "posted")
        self.assertEqual(post_account.remote_ref, remote_ref)
        self.assertEqual(post_account.post_account_url, post_account_url)

    @patch(PATCH_ACCOUNT_LINKEDIN.format("_request_linkedin"))
    def test_check_remote_post_exists_unreachable(self, mock_request):
        """LinkedIn out of reach leaves the publication untouched."""
        post_account = self.SocialPostAccountLinkedin
        post_account.write({"state": "posted"})
        mock_request.side_effect = UserError("boom")
        with mute_logger(LOGGER_POST_ACCOUNT_LINKEDIN):
            self.assertTrue(post_account.check_post_exists())
        self.assertEqual(post_account.state, "posted")

    @patch(PATCH_ACCOUNT_LINKEDIN.format("_request_linkedin"))
    def test_check_remote_post_exists_reads_the_post_endpoint(self, mock_request):
        """The check reads the publication itself, by its own reference."""
        post_account = self.SocialPostAccountLinkedin
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_request.return_value = mock_response
        self.assertTrue(post_account.check_post_exists())
        self.assertEqual(
            mock_request.call_args.kwargs["endpoint"],
            _ENDPOINT_POST_LINKEDIN % quote(post_account.remote_ref),
        )

    def _linkedin_suspects(self, refs, account=None):
        """Create a published line per reference on a LinkedIn account.

        The suspects of a batch are lines with a ``remote_ref`` the social
        media can be asked about, which is the only thing the confirmation
        reads from them.
        """
        account = account or self.SocialAccountLinkedin
        lines = self.SocialPostAccount.browse()
        for ref in refs:
            lines |= self.SocialPostAccount.create(
                {
                    "message": "Test Message",
                    "account_id": account.id,
                    "media_id": account.media_id.id,
                    "post_id": self.SocialPostLinkedin.id,
                    "remote_ref": ref,
                    "state": "posted",
                }
            )
        return lines

    def _batch_get_response(self, results=(), errors=None, status_code=200):
        """Answer a ``BATCH_GET`` of ``/posts`` the way LinkedIn does.

        ``results`` carries the publications it served, ``errors`` one entry
        per URN it refused, each with its own status.
        """
        response = MagicMock()
        response.status_code = status_code
        response.json.return_value = {
            "results": {urn: {"id": urn} for urn in results},
            "errors": errors or {},
        }
        return response

    @patch(PATCH_ACCOUNT_LINKEDIN.format("_request_linkedin"))
    def test_check_remote_posts_exist_confirms_only_the_404(self, mock_request):
        """The publication LinkedIn no longer serves is the confirmed one."""
        lines = self._linkedin_suspects(["urn:alive:1", "urn:gone", "urn:alive:2"])
        mock_request.return_value = self._batch_get_response(
            results=["urn:alive:1", "urn:alive:2"],
            errors={"urn:gone": {"status": 404, "message": "Not found"}},
        )
        gone = lines._check_remote_posts_exist()
        self.assertEqual(gone.mapped("remote_ref"), ["urn:gone"])
        self.assertEqual(mock_request.call_count, 1)
        self.assertEqual(
            mock_request.call_args.kwargs["endpoint"], _ENDPOINT_POSTS_LINKEDIN
        )
        self.assertEqual(mock_request.call_args.kwargs["params_fields"], ["ids"])
        self.assertEqual(
            sorted(mock_request.call_args.kwargs["params_values"]["ids"]),
            ["urn:alive:1", "urn:alive:2", "urn:gone"],
        )

    @patch(PATCH_ACCOUNT_LINKEDIN.format("_request_linkedin"))
    def test_check_remote_posts_exist_ignores_the_other_errors(self, mock_request):
        """A lost page role and a rate limit confirm no deletion at all."""
        lines = self._linkedin_suspects(["urn:forbidden", "urn:throttled"])
        mock_request.return_value = self._batch_get_response(
            errors={
                "urn:forbidden": {"status": 403, "message": "Not enough permissions"},
                "urn:throttled": {"status": 429, "message": "Too many requests"},
            },
        )
        self.assertFalse(lines._check_remote_posts_exist())
        self.assertEqual(lines.mapped("state"), ["posted", "posted"])

    @patch(PATCH_ACCOUNT_LINKEDIN.format("_request_linkedin"))
    def test_check_remote_posts_exist_ignores_an_unanswered_urn(self, mock_request):
        """A URN in neither block was not reported as gone either."""
        lines = self._linkedin_suspects(["urn:unanswered"])
        mock_request.return_value = self._batch_get_response()
        self.assertFalse(lines._check_remote_posts_exist())

    @patch(PATCH_ACCOUNT_LINKEDIN.format("_request_linkedin"))
    def test_check_remote_posts_exist_on_a_failed_answer(self, mock_request):
        """An answer that is not a 200 confirms nothing."""
        lines = self._linkedin_suspects(["urn:unknown"])
        mock_request.return_value = self._batch_get_response(status_code=500)
        with mute_logger(LOGGER_ACCOUNT_LINKEDIN):
            self.assertFalse(lines._check_remote_posts_exist())
        self.assertEqual(lines.state, "posted")

    @patch(PATCH_ACCOUNT_LINKEDIN.format("_request_linkedin"))
    def test_check_remote_posts_exist_when_linkedin_is_unreachable(self, mock_request):
        """A request that could not be made confirms nothing."""
        lines = self._linkedin_suspects(["urn:unreachable"])
        mock_request.side_effect = UserError("boom")
        with mute_logger(LOGGER_ACCOUNT_LINKEDIN):
            self.assertFalse(lines._check_remote_posts_exist())
        self.assertEqual(lines.state, "posted")

    @patch(PATCH_ACCOUNT_LINKEDIN.format("_request_linkedin"))
    def test_check_remote_posts_exist_asks_in_batches(self, mock_request):
        """Confirming costs one call per hundred suspects, not one each."""
        count = 2 * _BATCH_GET_MAX_IDS_LINKEDIN + 50
        lines = self._linkedin_suspects(
            ["urn:batch:%s" % index for index in range(count)]
        )
        mock_request.return_value = self._batch_get_response()
        self.assertFalse(lines._check_remote_posts_exist())
        self.assertEqual(mock_request.call_count, 3)
        self.assertEqual(
            sorted(
                len(call.kwargs["params_values"]["ids"])
                for call in mock_request.call_args_list
            ),
            [50, _BATCH_GET_MAX_IDS_LINKEDIN, _BATCH_GET_MAX_IDS_LINKEDIN],
        )

    @patch(PATCH_ACCOUNT_LINKEDIN.format("_request_linkedin"))
    def test_check_remote_posts_exist_asks_each_account_apart(self, mock_request):
        """A URN is asked about from the account that published it."""
        first = self._linkedin_suspects(["urn:first"])
        second = self._linkedin_suspects(
            ["urn:second"], account=self.SocialAccountLinkedinData
        )
        mock_request.return_value = self._batch_get_response()
        self.assertFalse((first | second)._check_remote_posts_exist())
        self.assertEqual(mock_request.call_count, 2)
        self.assertEqual(
            sorted(
                call.kwargs["params_values"]["ids"]
                for call in mock_request.call_args_list
            ),
            [["urn:first"], ["urn:second"]],
        )

    @patch(PATCH_ACCOUNT_LINKEDIN.format("_request_linkedin"))
    def test_check_remote_posts_exist_delegates_another_media(self, mock_request):
        """A line of another social media is answered by the generic side."""
        linkedin = self._linkedin_suspects(["urn:linkedin"])
        foreign = self.social_post_account_id
        foreign.write({"remote_ref": False, "state": "posted"})
        mock_request.return_value = self._batch_get_response()
        gone = (linkedin | foreign)._check_remote_posts_exist()
        self.assertEqual(gone, foreign)
        self.assertEqual(
            mock_request.call_args.kwargs["params_values"]["ids"], ["urn:linkedin"]
        )
