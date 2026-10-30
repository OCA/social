# Copyright 2026 Binhex <https://www.binhex.cloud>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from unittest.mock import MagicMock, patch

from tweepy.errors import Forbidden, Unauthorized

from odoo import Command
from odoo.exceptions import UserError
from odoo.tools import mute_logger

from odoo.addons.social_media_x.models.social_post import SocialPost as SocialPostX
from odoo.addons.social_media_x.social_x_utils import (
    _MAX_IMAGE_SIZE_X,
    _MAX_MESSAGE_LENGTH_PREMIUM_X,
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

    def test_check_account_ids_fires_when_the_accounts_change(self):
        """Adding the duplicate to a saved post is rejected too.

        The selection of accounts is what the check reads, so writing it is
        the moment the duplicate can appear.
        """
        post = self.SocialPost.create(
            {
                "message": "Test Message",
                "account_ids": [Command.set(self.SocialAccountCredentialX.ids)],
            }
        )
        account_repeat_username = self.SocialAccountCredentialX.copy()
        with self.assertRaises(UserError):
            post.write(
                {
                    "account_ids": [
                        Command.link(account_repeat_username.id),
                    ]
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
        self.assertFalse(post._get_post_errors("other_media"))

    def test_get_post_errors_message_too_long(self):
        post = self._draft_post(message="x" * (_MAX_MESSAGE_LENGTH_X + 1))
        self.assertIn("at most 280 characters", "\n".join(post._get_post_errors("x")))

    def test_get_post_errors_message_of_a_premium_account(self):
        """Premium buys characters, so the same post is refused or not."""
        post = self._draft_post(message="x" * (_MAX_MESSAGE_LENGTH_X + 1))
        self.assertIn("at most 280 characters", "\n".join(post._get_post_errors("x")))

        self.SocialAccountX.x_premium = True
        self.assertFalse(post._get_post_errors("x"))

        post.message = "x" * (_MAX_MESSAGE_LENGTH_PREMIUM_X + 1)
        self.assertIn("at most 25000 characters", "\n".join(post._get_post_errors("x")))

    def test_get_post_errors_measures_the_account_that_asks(self):
        """The publication asks with its account and gets its own limit."""
        premium = self.SocialAccountX.copy(
            {"username": "premium-username", "x_premium": True}
        )
        post = self._draft_post(message="x" * (_MAX_MESSAGE_LENGTH_X + 1))
        self.assertFalse(post._get_post_errors("x", account=premium))
        self.assertIn(
            "at most 280 characters",
            "\n".join(post._get_post_errors("x", account=self.SocialAccountX)),
        )

    def test_get_post_errors_takes_the_strictest_account_of_the_post(self):
        """The form asks once per social media, so it answers the minimum.

        The strictest account is the line that would fail, and a check that
        errs on the safe side is the one the form is allowed to show.
        """
        premium = self.SocialAccountX.copy(
            {"username": "premium-username", "x_premium": True}
        )
        post = self._draft_post(
            message="x" * (_MAX_MESSAGE_LENGTH_X + 1),
            account_ids=[Command.set((self.SocialAccountX + premium).ids)],
        )
        self.assertIn("at most 280 characters", "\n".join(post._get_post_errors("x")))

        self.SocialAccountX.x_premium = True
        self.assertFalse(post._get_post_errors("x"))

    def test_get_post_errors_without_any_account_of_x(self):
        """Nothing to resolve the limit with falls back to the strictest."""
        post = self._draft_post(
            message="x" * (_MAX_MESSAGE_LENGTH_X + 1),
            account_ids=[Command.clear()],
        )
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

    def test_post_preview_video_wins_over_the_images(self):
        """The preview shows the video, and the form still says X refuses it."""
        image = self.create_attachment("preview_image.jpg")
        video = self.create_attachment("preview_video.mp4")
        post = self._draft_post(
            image_ids=[Command.set(image.ids)],
            video_ids=[Command.set(video.ids)],
        )
        self.assertNotIn(f'"/web/image/{image.id}"', post.post_preview)
        self.assertIn("preview_video.mp4", post.post_preview)
        self.assertIn("either images or a video", post.message_error)

    def test_post_preview_video_hides_the_count_of_the_images(self):
        """No image is drawn, so the card does not count the ones left out."""
        images = (
            self.create_attachment("one.jpg")
            + self.create_attachment("two.jpg")
            + self.create_attachment("three.jpg")
        )
        post = self._draft_post(
            image_ids=[Command.set(images.ids)],
            video_ids=[Command.set(self.create_attachment("clip.mp4").ids)],
        )
        values = post._render_values_preview(self.media_x_id)
        self.assertFalse(values["image_ids"])
        self.assertEqual(values["hidden_image_count"], 0)
        for image in images:
            self.assertNotIn(f'"/web/image/{image.id}"', post.post_preview)
        self.assertNotIn("+1", post.post_preview)

    def test_post_preview_keeps_the_images_without_a_video(self):
        images = (
            self.create_attachment("one.jpg")
            + self.create_attachment("two.jpg")
            + self.create_attachment("three.jpg")
        )
        post = self._draft_post(image_ids=[Command.set(images.ids)])
        drawn = [
            image for image in images if f'"/web/image/{image.id}"' in post.post_preview
        ]
        self.assertEqual(len(drawn), 2)
        self.assertIn("+1", post.post_preview)

    def test_post_preview_leaves_the_other_media_alone(self):
        """What X refuses says nothing about the card of another media.

        The override of X is called directly over what the modules below it
        return, so the answer does not depend on whether LinkedIn is installed
        and adds its own rule for its own card.
        """
        post = self._draft_post(
            account_ids=[
                Command.set((self.SocialAccountX + self.social_account_id).ids)
            ],
            image_ids=[Command.set(self.create_attachment("one.jpg").ids)],
            video_ids=[Command.set(self.create_attachment("clip.mp4").ids)],
        )
        mro = type(post).mro()
        parent_cls = next(
            cls
            for cls in mro[mro.index(SocialPostX) + 1 :]
            if "_render_values_preview" in cls.__dict__
        )
        values_below = {"image_ids": post.image_ids, "hidden_image_count": 0}
        with self._fake_media_types(linkedin=self.social_media_id), patch.object(
            parent_cls,
            "_render_values_preview",
            autospec=True,
            return_value=values_below,
        ):
            values = SocialPostX._render_values_preview(post, self.social_media_id)
        self.assertEqual(values, values_below)

    def test_post_check_messages_show_the_errors_and_save_the_post(self):
        """The post is saved and the form says what X will not publish."""
        post = self._draft_post(message="x" * (_MAX_MESSAGE_LENGTH_X + 1))
        self.assertIn("at most 280 characters", post.message_error)
        self.assertFalse(post.message_info)

    def test_post_check_messages_follow_the_plan_of_the_account(self):
        """Turning Premium on refreshes the form of a post already written.

        The plan of an account is neither the accounts, nor the message, nor
        the media of the post, so without the redeclared dependency the
        banner would keep refusing a post that can already be published.
        """
        post = self._draft_post(message="x" * (_MAX_MESSAGE_LENGTH_X + 1))
        self.assertIn("at most 280 characters", post.message_error)

        self.SocialAccountX.x_premium = True
        self.assertFalse(post.message_error)

    @mute_logger("odoo.addons.social_media_base.models.social_post_account")
    def test_action_post_refuses_what_the_form_shows(self):
        """The publication fails its own line, with the text of the form.

        The message travels on both records because that is what publishing
        does: the post is what the form shows, the publication is what is
        measured, and ``_sync_pending_lines_message`` puts the text of the
        one on the other right before the line reaches the social media.
        """
        message = "x" * (_MAX_MESSAGE_LENGTH_X + 1)
        self.SocialPostAccountX.write(
            {"state": "ready", "remote_ref": False, "message": message}
        )
        self.SocialPostX.write({"message": message})
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

    @mute_logger("odoo.addons.social_media_base.models.social_post_account")
    def test_action_post_records_why_x_refused_the_post(self):
        """A post refused by X leaves its reason on the line, not raw text.

        The plan of an account is the one X answered when it was last read
        and can be out of date, so the refusal of X is what tells the user,
        and it has to name the cause.
        """
        post = self._draft_post(message="Test Message")
        self.SocialAccountX.x_premium = True
        with patch.object(
            type(self.SocialAccountX),
            "create_tweet",
            autospec=True,
            side_effect=UserError(
                "X refused the post of X Account: too long. What an account "
                "may publish depends on its plan, and X reported X Premium "
                "for this account when it was last read. Press Update account "
                "to read the plan again before trying again."
            ),
        ):
            post._action_create_post_account()
        line = post.post_account_ids
        self.assertEqual(line.state, "failed")
        self.assertIn("X Premium", line.failed_description)
        self.assertFalse(line.remote_ref)

    @mute_logger("odoo.addons.social_media_base.models.social_post_account")
    def test_action_post_forbidden_by_x_leaves_the_account_alone(self):
        """A 403 fails the line with its reason and flags nothing on the account.

        X answers a long post of an account read as X Premium that no longer
        holds the subscription with a 403, which authorizing the account again
        does not fix: the line tells the user to read the plan again, the post
        goes back to draft and the account is not asked to be authorized
        again.
        """
        self.SocialAccountX.x_premium = True
        post = self._draft_post(message="x" * 329)
        fake_client = MagicMock()
        fake_client.create_tweet.side_effect = self.get_x_refusal(
            Forbidden, 403, "You are not permitted to perform this action."
        )
        with self.get_patch_exceptions_x(
            fake_client=fake_client, valid_time_request=False
        ), patch.object(
            type(self.SocialAccountX),
            "_flag_credentials_expired",
            autospec=True,
        ) as mock_flag:
            post._action_create_post_account()
        line = post.post_account_ids
        self.assertEqual(line.state, "failed")
        self.assertIn("X Premium", line.failed_description)
        self.assertIn("Update account", line.failed_description)
        self.assertIn(
            "You are not permitted to perform this action.",
            line.failed_description,
        )
        self.assertFalse(line.remote_ref)
        self.assertEqual(post.state, "draft")
        self.assertFalse(self.SocialAccountX.need_update)
        mock_flag.assert_not_called()

    @mute_logger("odoo.addons.social_media_base.models.social_post_account")
    def test_action_post_unauthorized_by_x_flags_the_account(self):
        """A 401 fails the line and asks for the account to be authorized again.

        OAuth1 tokens of X never expire on their own dates, so a publication
        refused for credentials is how a revoked token shows up: the flag has
        to outlive the rollback of the publication that found it.
        """
        post = self._draft_post(message="Test Message")
        fake_client = MagicMock()
        fake_client.create_tweet.side_effect = self.get_x_refusal(
            Unauthorized, 401, "Unauthorized"
        )
        with self.get_patch_exceptions_x(
            fake_client=fake_client, valid_time_request=False
        ):
            post._action_create_post_account()
        line = post.post_account_ids
        self.assertEqual(line.state, "failed")
        self.assertFalse(line.remote_ref)
        self.assertEqual(post.state, "draft")
        self.assertTrue(self.SocialAccountX.need_update)

    @mute_logger("odoo.addons.social_media_base.models.social_post_account")
    def test_action_post_fails_only_the_account_the_message_is_too_long_for(self):
        """A limit of one account stops that account and nothing else.

        The publication that X already accepted keeps its reference: that is
        what the savepoint of ``_publish_guard`` is there to guarantee.
        """
        premium = self.SocialAccountX.copy(
            {"username": "premium-username", "x_premium": True}
        )
        post = self._draft_post(
            message="x" * (_MAX_MESSAGE_LENGTH_X + 1),
            account_ids=[Command.set((self.SocialAccountX + premium).ids)],
        )
        with patch.object(
            type(self.SocialAccountX),
            "create_tweet",
            autospec=True,
            return_value=("122809890045", {}),
        ) as mock_create_tweet:
            post._action_create_post_account()
        premium_line = post.post_account_ids.filtered(
            lambda one: one.account_id == premium
        )
        refused_line = post.post_account_ids - premium_line
        self.assertEqual(premium_line.state, "posted")
        self.assertEqual(premium_line.remote_ref, "122809890045")
        self.assertEqual(refused_line.state, "failed")
        self.assertIn("at most 280 characters", refused_line.failed_description)
        mock_create_tweet.assert_called_once()
