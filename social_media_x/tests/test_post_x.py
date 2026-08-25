# Copyright 2026 Binhex <https://www.binhex.cloud>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from unittest.mock import patch

from odoo import Command
from odoo.exceptions import UserError

from odoo.addons.social_media_x.social_x_utils import (
    _MAX_IMAGE_SIZE_X,
    _MAX_MESSAGE_LENGTH_X,
)
from odoo.addons.social_media_x.tests.test_common_x import (
    TestSocialCommonX,
)


class TestSocialPostX(TestSocialCommonX):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

    def test_check_account_ids(self):
        account_repeat_username = self.SocialAccountCredentialX.copy()
        with self.assertRaises(UserError):
            self.SocialPost.create(
                {
                    "message": "Test Message",
                    "account_ids": [
                        Command.set(
                            [
                                self.SocialAccountCredentialX.id,
                                account_repeat_username.id,
                            ]
                        )
                    ],
                }
            )

    def test_check_account_ids_leaves_the_other_media_alone(self):
        """The X spam rule used to reject accounts of any other media."""
        accounts = self.SocialAccount.create(
            [
                {
                    "name": "Corporate desk",
                    "media_id": self.social_media_id.id,
                    "username": "shared-handle",
                },
                {
                    "name": "Developer desk",
                    "media_id": self.social_media_id.id,
                    "username": "shared-handle",
                },
            ]
        )
        post = self.SocialPost.create(
            {
                "message": "Test Message",
                "account_ids": [Command.set(accounts.ids)],
            }
        )
        self.assertEqual(post.account_ids, accounts)

    def test_default_account_ids_only_the_active_company(self):
        """An account of another allowed company is not preselected."""
        company = self.env["res.company"].create({"name": "Other Company"})
        other_account = self.SocialAccountX.copy({"company_id": company.id})
        self.assertNotIn(other_account.id, self.SocialPost._default_account_ids())
        self.assertIn(
            other_account.id,
            self.SocialPost.with_company(company)._default_account_ids(),
        )

    def test_check_account_ids_ignores_the_accounts_without_a_username(self):
        """An empty username is no X user, so it duplicates nothing."""
        accounts = self.SocialAccount.create(
            [
                {"name": "Pending A", "media_id": self.media_x_id.id},
                {"name": "Pending B", "media_id": self.media_x_id.id},
            ]
        )
        post = self.SocialPost.create(
            {
                "message": "Test Message",
                "account_ids": [Command.set(accounts.ids)],
            }
        )
        self.assertEqual(post.account_ids, accounts)

    def _draft_post(self, **values):
        """Create a post of the X account that nothing has published yet.

        The post of the common setup already carries a publication with its
        remote reference, so its content is locked and cannot be written on.
        """
        return self.SocialPost.create(
            dict(
                {
                    "message": "Test Message",
                    "account_ids": [Command.set(self.SocialAccountX.ids)],
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
            errors = post._get_post_errors("x")
        self.assertEqual(errors, ["Refused by another module"])
        mock_super.assert_called_once()

    def test_get_post_warnings_calls_super(self):
        """X changes nothing about a post, but it still asks the others."""
        post = self._draft_post()
        parent_cls = self._get_parent_class_defining(post, "_get_post_warnings")
        with patch.object(
            parent_cls,
            "_get_post_warnings",
            autospec=True,
            return_value=["Changed by another module"],
        ) as mock_super:
            warnings = post._get_post_warnings("x")
        self.assertEqual(warnings, ["Changed by another module"])
        mock_super.assert_called_once()

    def test_get_post_errors_leaves_the_other_media_alone(self):
        """A rule of X says nothing about a post published elsewhere."""
        post = self._draft_post(message="x" * (_MAX_MESSAGE_LENGTH_X + 1))
        self.assertFalse(post._get_post_errors("linkedin"))

    def test_get_post_errors_message_too_long(self):
        post = self._draft_post(message="x" * (_MAX_MESSAGE_LENGTH_X + 1))
        self.assertIn("at most 280 characters", "\n".join(post._get_post_errors("x")))

    def test_get_post_errors_too_many_images(self):
        post = self._draft_post(
            image_ids=[
                Command.set(
                    [
                        self.create_attachment(f"image_{number}.jpg").id
                        for number in range(5)
                    ]
                )
            ]
        )
        self.assertIn("at most 4 images", "\n".join(post._get_post_errors("x")))

    def test_get_post_errors_several_videos(self):
        post = self._draft_post(
            video_ids=[
                Command.set(
                    [
                        self.create_attachment("one.mp4").id,
                        self.create_attachment("two.mp4").id,
                    ]
                )
            ]
        )
        self.assertIn("single video per post", "\n".join(post._get_post_errors("x")))

    def test_get_post_errors_images_and_video(self):
        """X takes one kind of media or the other, so this is not a warning."""
        post = self._draft_post(
            image_ids=[Command.set([self.create_attachment("one.jpg").id])],
            video_ids=[Command.set([self.create_attachment("clip.mp4").id])],
        )
        self.assertIn("either images or a video", "\n".join(post._get_post_errors("x")))
        self.assertFalse(post._get_post_warnings("x"))

    def test_get_post_errors_takes_webp_and_refuses_the_rest(self):
        """WEBP is published, unlike on LinkedIn; TIFF is not."""
        post = self._draft_post(
            image_ids=[Command.set([self.create_attachment("picture.webp").id])]
        )
        self.assertFalse(post._get_post_errors("x"))

        post.write(
            {"image_ids": [Command.set([self.create_attachment("scan.tiff").id])]}
        )
        self.assertIn(
            "JPG, PNG, WEBP and GIF images", "\n".join(post._get_post_errors("x"))
        )

    def test_get_post_errors_unsupported_video(self):
        post = self._draft_post(
            video_ids=[Command.set([self.create_attachment("holidays.mov").id])]
        )
        self.assertIn("MP4 videos", "\n".join(post._get_post_errors("x")))

    def test_get_post_errors_image_too_large(self):
        image = self.create_attachment("picture.webp", size=_MAX_IMAGE_SIZE_X + 1)
        post = self._draft_post(image_ids=[Command.set(image.ids)])
        self.assertIn("images of at most", "\n".join(post._get_post_errors("x")))

    def test_get_post_errors_gif_weighs_more_than_an_image(self):
        """A GIF travels as an image but carries its own, larger limit."""
        animation = self.create_attachment("animation.gif", size=_MAX_IMAGE_SIZE_X + 1)
        post = self._draft_post(image_ids=[Command.set(animation.ids)])
        self.assertFalse(post._get_post_errors("x"))

    def test_post_check_messages_show_the_errors_and_save_the_post(self):
        """The post is saved and the form says what X will not publish."""
        post = self._draft_post(message="x" * (_MAX_MESSAGE_LENGTH_X + 1))
        self.assertIn("at most 280 characters", post.message_error)
        self.assertFalse(post.message_info)

    def test_action_post_refuses_what_the_form_shows(self):
        """The publication fails its own line, with the text of the form."""
        self.SocialPostAccountX.write({"state": "ready", "remote_ref": False})
        self.SocialPostX.write({"message": "x" * (_MAX_MESSAGE_LENGTH_X + 1)})
        with patch.object(
            type(self.SocialPostX),
            "_filter_by_media_types",
            autospec=True,
            return_value=self.SocialPostAccountX,
        ), patch.object(
            type(self.SocialPostAccountX.account_id),
            "create_tweet",
            autospec=True,
        ) as mock_create_tweet:
            self.SocialPostAccountX._action_post(self.SocialPostX)
            mock_create_tweet.assert_not_called()
        self.assertEqual(self.SocialPostAccountX.state, "failed")
        self.assertIn(
            "at most 280 characters", self.SocialPostAccountX.failed_description
        )
