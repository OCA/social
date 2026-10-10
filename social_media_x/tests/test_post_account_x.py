# Copyright 2026 Binhex <https://www.binhex.cloud>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from unittest.mock import MagicMock, patch

from odoo import Command
from odoo.exceptions import UserError
from odoo.tools import mute_logger

from odoo.addons.social_media_base.tests.test_social_common import PATCH_POST_ACCOUNT
from odoo.addons.social_media_x.tests.test_common_x import (
    PATCH_ACCOUNT_X,
    TestSocialCommonX,
)

LOGGER_POST_ACCOUNT_X = "odoo.addons.social_media_x.models.social_post_account"


class TestSocialPostAccountX(TestSocialCommonX):
    def test_compute_post_statistics_x(self):
        post_account_values = {
            "post_id": self.SocialPostX.id,
            "account_id": self.SocialAccountX.id,
            "message": "Message Test XX",
            "click_count": 5,
            "comment_count": 2,
            "retweet_count": 3,
            "quote_count": 2,
        }
        self.SocialPostAccount.create(post_account_values)
        post_account_values.update(
            {
                "message": "Message Test X",
                "click_count": 5,
                "comment_count": 1,
                "retweet_count": 5,
                "quote_count": 1,
            }
        )
        self.SocialPostAccount.create(post_account_values)
        expected = (5 + 5) + (2 + 1) + (3 + 5) + (2 + 1)
        self.assertEqual(self.SocialPostX.count_post_interactions, expected)

    def test_interactions_count_adds_the_retweets_and_the_quotes(self):
        post_account = self.SocialPostAccount.create(
            {
                "post_id": self.SocialPostX.id,
                "account_id": self.SocialAccountX.id,
                "message": "Message Test X interactions",
                "click_count": 1,
                "like_count": 2,
                "comment_count": 3,
                "share_count": 4,
                "retweet_count": 5,
                "quote_count": 6,
            }
        )
        self.assertEqual(post_account.interactions_count, 21)

    @patch(PATCH_ACCOUNT_X.format("SocialAccount.get_client_api"))
    @patch(PATCH_POST_ACCOUNT.format("_delete_post_account"))
    @patch(PATCH_ACCOUNT_X.format("SocialAccount._valid_time_request"))
    def test_delete_post_account(
        self, mock_valid_time_request, mock_delete_post_account, mock_get_client_api
    ):
        mock_get_client_api.delete_tweet.return_value = True
        mock_valid_time_request.return_value = True
        self.SocialPostAccountX._delete_post_account()
        mock_delete_post_account.assert_called_once()

    @mute_logger(LOGGER_POST_ACCOUNT_X)
    def test_delete_post_account_exception(self):
        fake_client = MagicMock()
        fake_client.delete_tweet.side_effect = Exception("Error Delete Post")
        (
            mock_get_client_api,
            mock_valid_time_request,
        ) = self.get_patch_exceptions_x(fake_client)
        with mock_get_client_api, mock_valid_time_request:
            with self.assertRaises(Exception) as ctx:
                self.SocialPostAccountX._delete_post_account()
            self.assertIn("Error Delete Post", str(ctx.exception))

    def test_delete_post_account_without_remote_ref_spares_the_quota(self):
        """A line that never reached X asks X nothing, not even the quota.

        ``_valid_time_request`` warns the user when the window is still open,
        so asking it about a deletion that is going to be skipped is a quota
        notice for a request nobody makes.
        """
        post_account = self.SocialPostAccount.create(
            {
                "message": "Never published",
                "account_id": self.SocialAccountX.id,
                "media_id": self.media_x_id.id,
                "post_id": self.SocialPostX.id,
                "state": "failed",
            }
        )
        self.assertFalse(post_account.remote_ref)
        account_class = type(post_account.account_id)
        with (
            patch.object(
                account_class,
                "_valid_time_request",
                autospec=True,
                return_value=True,
            ) as valid_time_request,
            patch.object(
                account_class,
                "get_client_api",
                autospec=True,
                return_value=MagicMock(),
            ) as get_client_api,
        ):
            post_account._delete_post_account()
        valid_time_request.assert_not_called()
        get_client_api.assert_not_called()

    def test_delete_post_account_reports_what_x_answered(self):
        """A deletion X refused says why, in the words X used.

        tweepy answers the errors as dicts, so joining them as strings raised
        a ``TypeError`` of ours that hid the reason X gave.
        """
        fake_client = MagicMock()
        fake_client.delete_tweet.return_value = MagicMock(
            errors=[
                {"detail": "You are not allowed to delete this Tweet."},
                {"title": "Unsupported Authentication"},
            ]
        )
        (
            mock_get_client_api,
            mock_valid_time_request,
        ) = self.get_patch_exceptions_x(fake_client)
        with mock_get_client_api, mock_valid_time_request:
            with self.assertRaises(UserError) as ctx:
                self.SocialPostAccountX._delete_post_account()
        message = str(ctx.exception)
        self.assertIn("You are not allowed to delete this Tweet.", message)
        self.assertIn("Unsupported Authentication", message)
        self.assertNotIn("expected str instance", message)

    def test_delete_post_account_exception_manyrequests(self):
        """A deletion X refused for quota stops the whole deletion.

        The line is the only place holding ``remote_ref``, so letting the
        caller unlink it after X kept the tweet leaves the publication alive
        with nothing in Odoo pointing at it.
        """
        fake_client = MagicMock()
        fake_client.delete_tweet.side_effect = self.get_exception_manyrequests()
        (
            mock_get_client_api,
            mock_valid_time_request,
            mock_many_requests,
        ) = self.get_patch_exceptions_x(fake_client, True)
        with (
            mock_get_client_api,
            mock_valid_time_request,
            mock_many_requests as many_requests,
        ):
            with self.assertRaises(UserError) as ctx:
                self.SocialPostAccountX._delete_post_account()
        many_requests.assert_called_once()
        self.assertIn("limit of requests", str(ctx.exception))

    def test_delete_post_account_inside_the_quota_window_is_not_a_deletion(self):
        """The window of the endpoint still open is not a deleted post.

        Nothing is asked to X while the limit lasts, so the deletion says it
        could not happen instead of letting the line go.
        """
        mock_get_client_api = self.get_patch_exceptions_x(
            MagicMock(), valid_time_request=False
        )
        with (
            mock_get_client_api as get_client_api,
            patch.object(
                type(self.SocialPostAccountX.account_id),
                "_valid_time_request",
                autospec=True,
                return_value=False,
            ),
        ):
            with self.assertRaises(UserError) as ctx:
                self.SocialPostAccountX._delete_post_account()
        get_client_api.assert_not_called()
        self.assertIn("limit of requests", str(ctx.exception))

    def test_action_delete_post_account_keeps_the_line_on_quota(self):
        """The publication survives a deletion X did not confirm."""
        post_account = self.SocialPostAccountX
        mock_get_client_api = self.get_patch_exceptions_x(
            MagicMock(), valid_time_request=False
        )
        with (
            mock_get_client_api,
            patch.object(
                type(post_account.account_id),
                "_valid_time_request",
                autospec=True,
                return_value=False,
            ),
        ):
            with self.assertRaises(UserError):
                post_account.action_delete_post_account()
        self.assertTrue(post_account.exists())
        self.assertTrue(post_account.remote_ref)

    def test_action_post(self):
        self.SocialPostAccountX.write({"state": "ready"})
        with patch.object(
            type(self.SocialPostX),
            "_filter_by_media_types",
            autospec=True,
            return_value=self.SocialPostAccountX,
        ) as mock_filter_by_media_types, patch.object(
            type(self.SocialPostAccountX.account_id),
            "create_tweet",
            autospec=True,
            return_value=("122809890045", {}),
        ) as mock_create_tweet:
            self.SocialPostAccountX._action_post(self.SocialPostX)
            self.assertEqual(self.SocialPostAccountX.remote_ref, "122809890045")
            self.assertEqual(self.SocialPostAccountX.state, "posted")
            self.assertIn(
                self.SocialPostAccountX.account_id.username,
                self.SocialPostAccountX.post_account_url,
            )
            mock_filter_by_media_types.assert_called_once()
            mock_create_tweet.assert_called_once()

    def test_action_post_stores_what_x_called_each_media(self):
        """The publication keeps the reference of every media it published."""
        # X publishes either images or a video, never both in one post.
        video = self.create_attachment("published_video.mp4")
        self.SocialPostAccountX.write(
            {
                "state": "ready",
                "remote_ref": False,
                # What the fan-out does: the publication points at the very
                # medias of the post.
                "video_ids": [Command.set(video.ids)],
            }
        )
        self.SocialPostX.write({"video_ids": [Command.set(video.ids)]})
        media_refs = {str(video.id): "media_1"}
        with patch.object(
            type(self.SocialPostX),
            "_filter_by_media_types",
            autospec=True,
            return_value=self.SocialPostAccountX,
        ), patch.object(
            type(self.SocialPostAccountX.account_id),
            "create_tweet",
            autospec=True,
            return_value=("122809890045", media_refs),
        ):
            self.SocialPostAccountX._action_post(self.SocialPostX)
        self.SocialPostAccountX.invalidate_recordset(["media_refs"])
        self.assertEqual(self.SocialPostAccountX.media_refs, media_refs)
        self.assertTrue(
            self.SocialPostAccountX.has_video,
            msg="The card of an X publication says that it carries a video.",
        )

    def test_action_post_keeps_the_upload_order_of_the_images(self):
        """X draws the medias in the order it receives them."""
        self.SocialPostAccountX.write({"state": "ready", "remote_ref": False})
        images = self.env["ir.attachment"].create(
            [
                {
                    "name": f"image_{number}.png",
                    "type": "binary",
                    "datas": self.image_base64,
                }
                for number in range(3)
            ]
        )
        self.SocialPostX.write({"image_ids": [Command.set(images.ids)]})
        # Read back from database: a many2many follows the ``id desc`` order
        # of ``ir.attachment``, which is the order the cron would publish.
        self.SocialPostX.invalidate_recordset()
        with patch.object(
            type(self.SocialPostX),
            "_filter_by_media_types",
            autospec=True,
            return_value=self.SocialPostAccountX,
        ), patch.object(
            type(self.SocialPostAccountX.account_id),
            "create_tweet",
            autospec=True,
            return_value=("122809890045", {}),
        ) as mock_create_tweet:
            self.SocialPostAccountX._action_post(self.SocialPostX)
        self.assertEqual(
            list(mock_create_tweet.call_args.kwargs["image_ids"].ids), images.ids
        )

    def test_action_post_failed(self):
        self.SocialPostAccountX.write({"state": "ready"})
        with patch.object(
            type(self.SocialPostX),
            "_filter_by_media_types",
            autospec=True,
            return_value=self.SocialPostAccountX,
        ) as mock_filter_by_media_types, patch.object(
            type(self.SocialPostAccountX.account_id),
            "create_tweet",
            autospec=True,
            return_value=(False, {}),
        ) as mock_create_tweet:
            self.SocialPostAccountX._action_post(self.SocialPostX)
            self.assertEqual(self.SocialPostAccountX.state, "failed")
            mock_filter_by_media_types.assert_called_once()
            mock_create_tweet.assert_called_once()

    def test_interaction_count_fields_adds_the_retweets_and_the_quotes(self):
        """The hook is what feeds both the sum and its dependency."""
        self.assertEqual(
            self.SocialPostAccount._interaction_count_fields(),
            [
                "click_count",
                "like_count",
                "share_count",
                "comment_count",
                "retweet_count",
                "quote_count",
            ],
        )

    def test_check_remote_post_exists(self):
        fake_response = MagicMock()
        fake_response.errors = False
        fake_client = MagicMock()
        fake_client.get_tweet.return_value = fake_response
        mock_get_client_api, mock_valid_time_request = self.get_patch_exceptions_x(
            fake_client
        )
        with mock_get_client_api, mock_valid_time_request:
            self.assertTrue(self.SocialPostAccountX.check_post_exists())

    def test_check_remote_post_exists_deleted(self):
        """Only the ``Not Found`` answer of X marks the post as deleted."""
        post_account = self.SocialPostAccountX
        remote_ref = post_account.remote_ref
        fake_response = MagicMock()
        fake_response.errors = [
            {"type": "https://api.twitter.com/2/problems/resource-not-found"}
        ]
        fake_client = MagicMock()
        fake_client.get_tweet.return_value = fake_response
        mock_get_client_api, mock_valid_time_request = self.get_patch_exceptions_x(
            fake_client
        )
        with mock_get_client_api, mock_valid_time_request:
            self.assertFalse(post_account.check_post_exists())
        self.assertEqual(post_account.state, "deleted")
        self.assertFalse(post_account.post_account_url)
        self.assertEqual(post_account.remote_ref, remote_ref)

    @mute_logger(LOGGER_POST_ACCOUNT_X)
    def test_check_remote_post_exists_errors(self):
        """Any other error leaves the publication alone."""
        post_account = self.SocialPostAccountX
        post_account.write({"state": "posted"})
        fake_response = MagicMock()
        fake_response.errors = ["Error 1", "Error 2"]
        fake_client = MagicMock()
        fake_client.get_tweet.return_value = fake_response
        mock_get_client_api, mock_valid_time_request = self.get_patch_exceptions_x(
            fake_client
        )
        with mock_get_client_api, mock_valid_time_request:
            self.assertTrue(post_account.check_post_exists())
        self.assertEqual(post_account.state, "posted")

    @mute_logger(LOGGER_POST_ACCOUNT_X)
    def test_check_remote_post_exists_exception(self):
        post_account = self.SocialPostAccountX
        post_account.write({"state": "posted"})
        fake_client = MagicMock()
        fake_client.get_tweet.side_effect = Exception("Error Get Comment")
        (
            mock_get_client_api,
            mock_valid_time_request,
        ) = self.get_patch_exceptions_x(fake_client)
        with mock_get_client_api, mock_valid_time_request:
            self.assertTrue(post_account.check_post_exists())
        self.assertEqual(post_account.state, "posted")

    def test_check_remote_post_exists_manyrequests(self):
        post_account = self.SocialPostAccountX
        post_account.write({"state": "posted"})
        fake_client = MagicMock()
        fake_client.get_tweet.return_value = False
        fake_client.get_tweet.side_effect = self.get_exception_manyrequests()
        (
            mock_get_client_api,
            mock_valid_time_request,
            mock_many_requests,
        ) = self.get_patch_exceptions_x(fake_client, True)
        with (
            mock_get_client_api,
            mock_valid_time_request,
            mock_many_requests as many_requests,
        ):
            self.assertTrue(post_account.check_post_exists())
        many_requests.assert_called_once()
        self.assertEqual(post_account.state, "posted")
