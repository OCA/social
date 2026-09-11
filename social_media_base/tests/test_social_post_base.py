# Copyright 2026 Binhex <https://www.binhex.cloud>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import json
from ast import literal_eval
from datetime import datetime, timedelta
from unittest.mock import patch

import psycopg2
from freezegun import freeze_time
from psycopg2 import errorcodes

from odoo import _, fields
from odoo.exceptions import UserError, ValidationError
from odoo.fields import Command
from odoo.tests.common import tagged
from odoo.tools import mute_logger

from odoo.addons.social_media_base.exceptions import SocialCredentialsError
from odoo.addons.social_media_base.tests.test_social_common import (
    TestSocialMediaBaseCommon,
)

LOGGER_POST = "odoo.addons.social_media_base.models.social_post"
LOGGER_POST_ACCOUNT = "odoo.addons.social_media_base.models.social_post_account"


class TestSocialPostBase(TestSocialMediaBaseCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.other_account_id = cls.SocialAccount.create(
            {
                "name": "Linkedin second account",
                "media_id": cls.social_media_id.id,
                "username": "linkedin_second_account",
            }
        )

    def _create_scheduled_post(self, minutes=5):
        """Create a scheduled post whose date is ``minutes`` from now.

        The date is always in the future: a post cannot be planned for a date
        already reached. The tests that need an overdue post move the clock
        forward instead.
        """
        post = self.SocialPost.create(
            {
                "message": "Scheduled message",
                "account_ids": [Command.set([self.social_account_id.id])],
                "send_post": "schedule",
            }
        )
        post.send_post_date = fields.Datetime.now() + timedelta(minutes=minutes)
        return post

    @freeze_time("2026-01-15 10:00:00")
    def test_compute_send_post_date(self):
        self.social_post_id.send_post = "schedule"
        self.social_post_id._compute_send_post_date()
        self.assertEqual(
            self.social_post_id.send_post_date,
            datetime(2026, 1, 15, 11, 0, 0),
        )
        self.assertEqual(self.social_post_id.state, "planned")

    def test_send_post_date_is_editable(self):
        """The computed date is only a proposal: the user can change it."""
        post = self._create_scheduled_post(minutes=30)
        chosen_date = fields.Datetime.now() + timedelta(days=2)
        post.send_post_date = chosen_date
        post.invalidate_recordset()
        self.assertEqual(post.send_post_date, chosen_date)

    def test_a_post_cannot_be_scheduled_in_the_past(self):
        post = self._create_scheduled_post(minutes=30)
        with self.assertRaises(ValidationError):
            post.send_post_date = fields.Datetime.now() - timedelta(minutes=1)

    def test_a_post_cannot_be_created_scheduled_in_the_past(self):
        with self.assertRaises(ValidationError):
            self.SocialPost.create(
                {
                    "message": "Late message",
                    "account_ids": [Command.set([self.social_account_id.id])],
                    "send_post": "schedule",
                    "send_post_date": fields.Datetime.now() - timedelta(minutes=1),
                }
            )

    def test_a_published_post_keeps_its_date_once_it_is_past(self):
        """The date of a post already sent is history, not a schedule."""
        post = self._create_scheduled_post()
        with freeze_time(fields.Datetime.now() + timedelta(minutes=10)):
            post.write({"state": "published"})
            post.write({"message": "Edited after the publication"})
        self.assertEqual(post.message, "Edited after the publication")
        self.assertEqual(post.state, "published")

    def test_a_planned_post_still_offers_the_post_button(self):
        """A schedule says when the cron sends, not that the user gave up."""
        post = self._create_scheduled_post(minutes=30)
        self.assertEqual(post.state, "planned")
        self.assertFalse(post.hide_post)
        post.account_ids = [Command.clear()]
        self.assertTrue(post.hide_post)

    def test_a_planned_post_published_by_hand_keeps_its_schedule_date(self):
        """Publishing right away is not a reschedule: the date is history."""
        post = self._create_scheduled_post(minutes=30)
        scheduled_date = post.send_post_date

        def _post(records, post_id):
            post_id.post_account_ids.write({"state": "posted"})

        with patch.object(
            type(self.social_post_account_id),
            "_action_post",
            autospec=True,
            side_effect=_post,
        ):
            post.action_create_post_account()
        self.assertEqual(post.state, "published")
        self.assertTrue(post.published_date)
        self.assertEqual(post.send_post, "schedule")
        self.assertEqual(post.send_post_date, scheduled_date)
        self.assertTrue(post.hide_post)

    def test_unarchiving_a_post_resets_its_overdue_schedule(self):
        """Any way back to active goes through write, not only the account."""
        post = self._create_scheduled_post(minutes=30)
        post.action_archive()
        with freeze_time(fields.Datetime.now() + timedelta(hours=1)):
            post.action_unarchive()
        self.assertTrue(post.active)
        self.assertEqual(post.state, "draft")

    def test_unarchiving_the_account_resets_the_overdue_schedule(self):
        """The account keeps restoring its posts through the same path."""
        post = self._create_scheduled_post(minutes=30)
        self.social_account_id.action_archive()
        self.assertFalse(post.active)
        with freeze_time(fields.Datetime.now() + timedelta(hours=1)):
            self.social_account_id.action_unarchive()
        self.assertTrue(post.active)
        self.assertEqual(post.state, "draft")

    def test_a_post_without_active_account_is_not_published(self):
        """An empty account list must not read as "everything went fine"."""
        post = self.SocialPost.create(
            {
                "message": "Message of an archived account",
                "account_ids": [Command.set([self.social_account_id.id])],
            }
        )
        self.social_account_id.action_archive()
        post.action_unarchive()
        self.assertFalse(post.account_ids)
        with self.assertRaises(UserError):
            post.action_create_post_account()
        self.assertNotEqual(post.state, "published")
        self.assertFalse(post.published_date)

    def test_run_send_post_only_sends_the_due_scheduled_posts(self):
        due_post = self._create_scheduled_post()
        not_due_post = self._create_scheduled_post(minutes=60)
        with freeze_time(fields.Datetime.now() + timedelta(minutes=10)), patch.object(
            type(self.social_post_id),
            "_action_create_post_account",
            autospec=True,
        ) as mock_create:
            self.SocialPost._run_send_post()
        self.assertEqual(mock_create.call_count, 1)
        sent_post = mock_create.call_args[0][0]
        self.assertEqual(sent_post.id, due_post.id)
        self.assertNotEqual(sent_post.id, not_due_post.id)
        self.assertEqual(self.social_post_id.send_post, "now")
        self.assertTrue(sent_post.env.context.get("social_post_cron"))

    def test_run_send_post_isolates_a_failing_post(self):
        failing_post = self._create_scheduled_post()
        other_post = self._create_scheduled_post()
        sent_ids = []

        def _publish(post):
            if post.id == failing_post.id:
                raise UserError(_("The post could not be sent"))
            sent_ids.append(post.id)

        with freeze_time(fields.Datetime.now() + timedelta(minutes=10)), patch.object(
            type(self.social_post_id),
            "_action_create_post_account",
            autospec=True,
            side_effect=_publish,
        ), mute_logger(LOGGER_POST):
            self.SocialPost._run_send_post()
        self.assertEqual(sent_ids, [other_post.id])
        self.assertEqual(failing_post.state, "draft")
        self.assertTrue(
            failing_post.message_ids.filtered(
                lambda message: "The post could not be sent" in (message.body or "")
            )
        )

    def test_run_send_post_keeps_planned_an_unexpected_failure(self):
        """A failure that may solve itself is worth retrying on the next run."""
        failing_post = self._create_scheduled_post()

        def _publish(post):
            raise ValueError("LinkedIn is unreachable")

        with freeze_time(fields.Datetime.now() + timedelta(minutes=10)), patch.object(
            type(self.social_post_id),
            "_action_create_post_account",
            autospec=True,
            side_effect=_publish,
        ), mute_logger(LOGGER_POST):
            self.SocialPost._run_send_post()
        self.assertEqual(failing_post.state, "planned")
        self.assertTrue(
            failing_post.message_ids.filtered(
                lambda message: "LinkedIn is unreachable" in (message.body or "")
            )
        )

    def test_publish_guard_marks_the_line_as_failed(self):
        post_account = self.social_post_account_id
        with mute_logger(LOGGER_POST_ACCOUNT), post_account._publish_guard():
            raise UserError(_("LinkedIn refused the post"))
        self.assertEqual(post_account.state, "failed")
        self.assertIn("LinkedIn refused the post", post_account.failed_description)
        self.assertTrue(
            post_account.post_id.message_ids.filtered(
                lambda message: "LinkedIn refused the post" in (message.body or "")
            )
        )

    def test_a_failed_publication_brings_the_post_button_back(self):
        """The button is computed from the state of the publications.

        A line that fails during the publication has to invalidate the post
        that carries it, otherwise the retry button stays hidden until the
        next request.
        """
        post = self.social_post_id
        post.write({"state": "publishing"})
        self.assertFalse(post.any_failed_post)
        self.assertTrue(post.hide_post)
        with mute_logger(
            LOGGER_POST_ACCOUNT
        ), self.social_post_account_id._publish_guard():
            raise UserError(_("LinkedIn refused the post"))
        self.assertTrue(post.any_failed_post)
        self.assertFalse(post.hide_post)

    def test_publish_attempt_renews_the_credentials_first(self):
        """Publishing on an account is what makes its token be checked."""
        post_account = self.social_post_account_id
        with patch.object(
            type(self.social_account_id),
            "validate_access_token",
            autospec=True,
        ) as mock_validate:
            post_account._publish_attempt(lambda **kwargs: "urn:li:share:1")
        mock_validate.assert_called_once()
        self.assertTrue(
            mock_validate.call_args[0][0].env.context.get("not_notify"),
            "Publishing is not the moment to tell the user that the token works",
        )

    def test_publish_attempt_fails_the_line_when_the_token_cannot_be_renewed(self):
        post_account = self.social_post_account_id
        calls = []
        with mute_logger(LOGGER_POST_ACCOUNT), patch.object(
            type(self.social_account_id),
            "validate_access_token",
            autospec=True,
            side_effect=UserError(_("The token could not be renewed")),
        ), post_account._publish_guard():
            post_account._publish_attempt(lambda **kwargs: calls.append(kwargs))
        self.assertFalse(calls, "Nothing must be sent without valid credentials")
        self.assertEqual(post_account.state, "failed")
        self.assertIn("The token could not be renewed", post_account.failed_description)

    def test_publish_attempt_publishes_again_once_the_token_is_renewed(self):
        post_account = self.social_post_account_id
        calls = []

        def publish(**kwargs):
            calls.append(kwargs)
            if len(calls) == 1:
                raise SocialCredentialsError(_("The access token expired"))
            return "urn:li:share:1"

        with patch.object(
            type(self.social_account_id),
            "_refresh_credentials",
            autospec=True,
            return_value=True,
        ) as mock_refresh:
            result = post_account._publish_attempt(publish, message="Hello")
        mock_refresh.assert_called_once()
        self.assertEqual(result, "urn:li:share:1")
        self.assertEqual(calls, [{"message": "Hello"}, {"message": "Hello"}])

    def test_publish_attempt_flags_the_account_it_cannot_renew(self):
        """The error is caught by hand: ``assertRaises`` would undo the flag."""
        post_account = self.social_post_account_id
        account = self.social_account_id

        def publish(**kwargs):
            raise SocialCredentialsError(_("The access token was revoked"))

        refused = False
        with patch.object(
            type(account),
            "_refresh_credentials",
            autospec=True,
            return_value=False,
        ):
            try:
                post_account._publish_attempt(publish)
            except SocialCredentialsError:
                refused = True
        self.assertTrue(refused)
        self.assertTrue(account.need_update)
        self.assertTrue(
            account.message_ids.filtered(
                lambda message: "The access token was revoked" in (message.body or "")
                and account.user_id.partner_id in message.partner_ids
            )
        )

    def test_publish_attempt_does_not_retry_another_error(self):
        post_account = self.social_post_account_id
        calls = []

        def publish(**kwargs):
            calls.append(kwargs)
            raise UserError(_("The message is too long"))

        with self.assertRaises(UserError), patch.object(
            type(self.social_account_id),
            "_refresh_credentials",
            autospec=True,
        ) as mock_refresh:
            post_account._publish_attempt(publish)
        mock_refresh.assert_not_called()
        self.assertEqual(len(calls), 1)

    def test_publish_guard_rolls_back_the_partial_write(self):
        post_account = self.social_post_account_id
        with mute_logger(LOGGER_POST_ACCOUNT), post_account._publish_guard():
            post_account.remote_ref = "urn:li:share:1"
            raise UserError(_("The post could not be sent"))
        self.assertFalse(post_account.remote_ref)
        self.assertEqual(post_account.state, "failed")

    def test_publish_guard_reraises_concurrency_errors(self):
        """Concurrency errors must bubble up so the server retries."""

        class ConcurrencyError(psycopg2.OperationalError):
            pgcode = errorcodes.SERIALIZATION_FAILURE

        post_account = self.social_post_account_id
        with self.assertRaises(
            psycopg2.OperationalError
        ), post_account._publish_guard():
            raise ConcurrencyError("serialization conflict")
        self.assertNotEqual(post_account.state, "failed")

    def test_publish_guard_registers_a_plain_operational_error(self):
        """An operational error unrelated to concurrency fails the line."""
        post_account = self.social_post_account_id
        with mute_logger(LOGGER_POST_ACCOUNT), post_account._publish_guard():
            raise psycopg2.OperationalError("the connection was dropped")
        self.assertEqual(post_account.state, "failed")
        self.assertIn("the connection was dropped", post_account.failed_description)

    def test_publish_guard_keeps_the_changes_on_success(self):
        post_account = self.social_post_account_id
        with post_account._publish_guard():
            post_account.write({"remote_ref": "urn:li:share:2", "state": "posted"})
        self.assertEqual(post_account.remote_ref, "urn:li:share:2")
        self.assertEqual(post_account.state, "posted")

    def test_action_create_post_account(self):
        fake_post_account = [
            Command.create(
                {
                    "post_id": self.social_post_id.id,
                    "account_id": self.social_post_account_id.account_id.id,
                    "state": "ready",
                    "message": self.test_message,
                }
            )
        ]
        with patch.object(
            type(self.social_post_id),
            "_prepare_post_account_values",
            autospec=True,
            return_value=fake_post_account,
        ), patch.object(
            type(self.social_post_account_id),
            "_action_post",
            autospec=True,
        ) as mock_action_post:
            self.social_post_id._action_create_post_account()
            mock_action_post.assert_called_once_with(
                self.SocialPostAccount,
                post_id=self.social_post_id,
            )
            self.assertEqual(self.social_post_id.state, "publishing")
            self.assertEqual(len(self.social_post_id.post_account_ids), 2)

    def test_compute_display_name(self):
        self.social_post_id._compute_display_name()
        self.assertIn("Linkedin", self.social_post_id.display_name)

    def test_action_post(self):
        result = self.social_post_account_id._action_post({})
        self.assertIsNone(result)

    def test_action_open_statistics(self):
        """The card of the dashboard opens the figures in a dialog."""
        post_account = self.social_post_account_id
        view = self.env.ref(
            "social_media_base.social_post_account_view_form_statistics"
        )
        action = post_account.action_open_statistics()
        self.assertEqual(action["type"], "ir.actions.act_window")
        self.assertEqual(action["target"], "new")
        self.assertEqual(action["res_model"], "social.post.account")
        self.assertEqual(action["res_id"], post_account.id)
        self.assertEqual(action["views"], [(view.id, "form")])

    def test_action_open_statistics_is_about_one_publication(self):
        post = self.SocialPost.create(
            {
                "message": self.test_message,
                "account_ids": [Command.set(self.social_account_id.ids)],
            }
        )
        post_accounts = self.SocialPostAccount.create(
            [
                {
                    "message": self.test_message,
                    "account_id": self.social_account_id.id,
                    "post_id": post.id,
                }
                for __ in range(2)
            ]
        )
        with self.assertRaises(ValueError):
            post_accounts.action_open_statistics()

    def test_statistics_view_shows_the_figures_this_module_counts(self):
        """The dialog draws every figure of a publication, and when it was read.

        They are all this module's now: the connectors read them back for the
        recent publications, so none of them waits for a synchronization module
        to become a number.
        """
        # The arch of the record, not the one of get_view: what another
        # module adds with an xpath is that module's to test.
        arch = self.env.ref(
            "social_media_base.social_post_account_view_form_statistics"
        ).arch
        for field_name in (
            "link_click_count",
            "impression_count",
            "click_count",
            "share_count",
            "like_count",
            "comment_count",
            "interactions_count",
            "engagement",
            "statistics_date",
        ):
            self.assertIn(f'name="{field_name}"', arch)

    def test_delete_post_account_deletes_post_when_last_link(self):
        post = self.SocialPost.create(
            {
                "message": self.test_message,
                "account_ids": [Command.set(self.social_account_id.ids)],
            }
        )
        post_account = self.SocialPostAccount.create(
            {
                "message": self.test_message,
                "account_id": self.social_account_id.id,
                "post_id": post.id,
            }
        )
        with patch.object(
            type(post_account), "_delete_post_account", autospec=True
        ) as mocked_hook:
            action = post_account.action_delete_post_account()
            mocked_hook.assert_called_once_with(post_account)
        self.assertFalse(self.SocialPostAccount.browse(post_account.id).exists())
        self.assertFalse(self.SocialPost.browse(post.id).exists())
        self.assertEqual(action["type"], "ir.actions.client")
        self.assertEqual(action["tag"], "display_notification")
        params = action["params"]
        self.assertEqual(params["type"], "success")
        self.assertIn("Post deleted", params["title"])
        self.assertIn(self.social_account_id.name, params["title"])
        self.assertEqual(params["message"], "The post was successfully deleted.")
        self.assertEqual(params["next"], {"type": "ir.actions.client", "tag": "reload"})

    def test_delete_post_account_when_other_links_exist(self):
        post = self.SocialPost.create(
            {
                "message": self.test_message,
                "account_ids": [Command.set(self.social_account_id.ids)],
            }
        )
        post_account1 = self.SocialPostAccount.create(
            {
                "message": self.test_message,
                "account_id": self.social_account_id.id,
                "post_id": post.id,
            }
        )
        post_account2 = self.SocialPostAccount.create(
            {
                "message": self.test_message,
                "account_id": self.social_account_id.id,
                "post_id": post.id,
            }
        )
        with patch.object(type(post_account1), "_delete_post_account", autospec=True):
            action = post_account1.action_delete_post_account()
        self.assertFalse(self.SocialPostAccount.browse(post_account1.id).exists())
        self.assertTrue(self.SocialPostAccount.browse(post_account2.id).exists())
        self.assertTrue(self.SocialPost.browse(post.id).exists())
        self.assertEqual(action["type"], "ir.actions.client")
        self.assertEqual(action["tag"], "display_notification")

    def test_delete_post_account_keeps_the_line_when_the_cleanup_fails(self):
        """The remote publication is already gone: never roll that back."""
        post = self.SocialPost.create(
            {
                "message": self.test_message,
                "account_ids": [Command.set(self.social_account_id.ids)],
            }
        )
        post_account = self.SocialPostAccount.create(
            {
                "message": self.test_message,
                "account_id": self.social_account_id.id,
                "post_id": post.id,
                "remote_ref": "urn:li:share:3",
                "state": "posted",
            }
        )
        with mute_logger(LOGGER_POST_ACCOUNT), patch.object(
            type(post_account), "_delete_post_account", autospec=True
        ), patch.object(
            type(post), "unlink", side_effect=UserError(_("The post is locked"))
        ):
            action = post_account.action_delete_post_account()
        self.assertTrue(self.SocialPostAccount.browse(post_account.id).exists())
        self.assertEqual(post_account.state, "failed")
        self.assertFalse(post_account.remote_ref)
        self.assertIn("The post is locked", post_account.failed_description)
        self.assertEqual(action["params"]["type"], "danger")

    def test_delete_post_account_reraises_concurrency_errors(self):
        class ConcurrencyError(psycopg2.OperationalError):
            pgcode = errorcodes.SERIALIZATION_FAILURE

        post = self.SocialPost.create(
            {
                "message": self.test_message,
                "account_ids": [Command.set(self.social_account_id.ids)],
            }
        )
        post_account = self.SocialPostAccount.create(
            {
                "message": self.test_message,
                "account_id": self.social_account_id.id,
                "post_id": post.id,
            }
        )
        with self.assertRaises(psycopg2.OperationalError), patch.object(
            type(post_account), "_delete_post_account", autospec=True
        ), patch.object(
            type(post), "unlink", side_effect=ConcurrencyError("serialization conflict")
        ):
            post_account.action_delete_post_account()

    def _create_partially_published_post(self, scheduled=False):
        """Publish a post on two accounts where only the first one succeeds.

        :return: the post and its failed publication.
        """
        values = {
            "message": self.test_message,
            "account_ids": [
                Command.set((self.social_account_id | self.other_account_id).ids)
            ],
        }
        post = self.SocialPost.create(values)
        if scheduled:
            post.send_post = "schedule"
            post.send_post_date = fields.Datetime.now() + timedelta(minutes=5)

        def fake_action_post(records, post_id=None):
            for line in post_id.post_account_ids:
                if line.account_id == self.social_account_id:
                    line.write({"state": "posted", "remote_ref": "urn:posted"})
                else:
                    line.write({"state": "failed"})

        with patch.object(
            type(self.social_post_account_id),
            "_action_post",
            autospec=True,
            side_effect=fake_action_post,
        ):
            post._action_create_post_account()
        failed_line = post.post_account_ids.filtered(
            lambda line: line.state == "failed"
        )
        return post, failed_line

    def test_action_create_post_account_mixed_results(self):
        post, failed_line = self._create_partially_published_post()
        self.assertEqual(post.state, "partially_published")
        self.assertTrue(post.published_date)
        self.assertTrue(post.content_locked)
        self.assertTrue(failed_line)
        self.assertFalse(post.hide_post)

    def test_partially_published_post_notifies_the_failed_responsible(self):
        post, failed_line = self._create_partially_published_post()
        notification = post.message_ids.filtered(
            lambda message: "failed on" in (message.body or "")
        )
        self.assertTrue(notification)
        self.assertIn(
            failed_line.account_id.user_id.partner_id,
            notification.partner_ids,
        )

    def test_partially_published_post_is_retried_only_by_hand(self):
        post, failed_line = self._create_partially_published_post(scheduled=True)
        with freeze_time(fields.Datetime.now() + timedelta(minutes=10)), patch.object(
            type(self.social_post_id),
            "_action_create_post_account",
            autospec=True,
        ) as mock_create:
            self.SocialPost._run_send_post()
        mock_create.assert_not_called()

        def fake_action_post(records, post_id=None):
            failed_line.write({"state": "posted", "remote_ref": "urn:retried"})

        with patch.object(
            type(self.social_post_account_id),
            "_action_post",
            autospec=True,
            side_effect=fake_action_post,
        ):
            post.action_create_post_account()
        self.assertEqual(post.state, "published")

    def test_partially_published_post_survives_the_archive_round_trip(self):
        post, _failed_line = self._create_partially_published_post(scheduled=True)
        post.action_archive()
        with freeze_time(fields.Datetime.now() + timedelta(hours=1)):
            post.action_unarchive()
        self.assertEqual(post.state, "partially_published")
        self.assertTrue(post.content_locked)

    def test_a_published_post_cannot_be_cancelled(self):
        post, _failed_line = self._create_partially_published_post()
        with self.assertRaises(UserError):
            post.action_cancel()

    def test_the_content_of_a_published_post_cannot_be_changed(self):
        post, _failed_line = self._create_partially_published_post()
        post.state = "draft"
        for values in (
            {"message": "Another message"},
            {"account_ids": [Command.clear()]},
            {"send_post": "schedule"},
        ):
            with self.assertRaises(UserError):
                post.write(values)
        self.assertEqual(post.message, self.test_message)

    def test_an_archived_publication_still_locks_the_post(self):
        """Archiving never removed anything from the social media."""
        post, _failed_line = self._create_partially_published_post()
        post.post_account_ids.write({"active": False})
        post.invalidate_recordset()
        self.assertFalse(post.post_account_ids)
        self.assertTrue(post.content_locked)

    def test_a_retry_keeps_the_message_that_is_already_online(self):
        post, failed_line = self._create_partially_published_post()
        post.post_account_ids.write({"message": "Message really sent"})
        with patch.object(
            type(self.social_post_account_id),
            "_action_post",
            autospec=True,
        ):
            post.action_create_post_account()
        self.assertEqual(failed_line.message, "Message really sent")

    def test_a_post_that_failed_everywhere_is_retried_with_its_new_message(self):
        post = self.SocialPost.create(
            {
                "message": self.test_message,
                "account_ids": [Command.set(self.social_account_id.ids)],
            }
        )

        def fake_action_post(records, post_id=None):
            post_id.post_account_ids.write({"state": "failed"})

        with patch.object(
            type(self.social_post_account_id),
            "_action_post",
            autospec=True,
            side_effect=fake_action_post,
        ):
            post._action_create_post_account()
        self.assertEqual(post.state, "draft")
        self.assertFalse(post.content_locked)
        post.message = "Corrected message"
        with patch.object(
            type(self.social_post_account_id),
            "_action_post",
            autospec=True,
        ):
            post.action_create_post_account()
        self.assertEqual(len(post.post_account_ids), 1)
        self.assertEqual(post.post_account_ids.message, "Corrected message")

    def test_action_create_post_account_public_wrapper(self):
        with patch.object(
            type(self.social_post_id),
            "_action_create_post_account",
            autospec=True,
        ) as mocked:
            self.social_post_id.action_create_post_account()
        mocked.assert_called_once()

    def test_action_create_post_account_all_posted(self):
        post = self.SocialPost.create(
            {
                "message": self.test_message,
                "account_ids": [Command.set(self.social_account_id.ids)],
            }
        )

        def fake_action_post(records, post_id=None):
            post_id.post_account_ids.write({"state": "posted"})

        with patch.object(
            type(self.social_post_account_id),
            "_action_post",
            autospec=True,
            side_effect=fake_action_post,
        ):
            post._action_create_post_account()
        self.assertEqual(post.state, "published")
        self.assertTrue(post.published_date)

    def test_action_create_post_account_all_failed(self):
        post = self.SocialPost.create(
            {
                "message": self.test_message,
                "account_ids": [Command.set(self.social_account_id.ids)],
            }
        )

        def fake_action_post(records, post_id=None):
            post_id.post_account_ids.write({"state": "failed"})

        with patch.object(
            type(self.social_post_account_id),
            "_action_post",
            autospec=True,
            side_effect=fake_action_post,
        ):
            post._action_create_post_account()
        self.assertEqual(post.state, "draft")

    def test_post_check_messages_default(self):
        """A connector implementing nothing leaves both fields empty."""
        self.assertFalse(self.social_post_id.message_info)
        self.assertFalse(self.social_post_id.message_error)

    def test_get_post_errors_and_warnings_are_empty_in_base(self):
        """The two hooks are extension points: base itself objects to nothing."""
        self.assertEqual(self.social_post_id._get_post_errors("linkedin"), [])
        self.assertEqual(self.social_post_id._get_post_warnings("linkedin"), [])
        self.assertEqual(
            self.social_post_id._get_post_errors(
                "linkedin", account=self.social_account_id
            ),
            [],
        )

    def test_post_check_messages_asks_each_media_once(self):
        """Two accounts of the same social media ask that media a single time."""
        second_account = self.social_account_id.copy({"name": "Second account"})
        self.social_post_id.write(
            {
                "account_ids": [
                    Command.set((self.social_account_id | second_account).ids)
                ]
            }
        )
        with self._fake_media_types(alpha=self.social_media_id), patch.object(
            type(self.social_post_id),
            "_get_post_errors",
            autospec=True,
            return_value=["Refused"],
        ) as mock_errors, patch.object(
            type(self.social_post_id),
            "_get_post_warnings",
            autospec=True,
            return_value=["Changed"],
        ):
            self.social_post_id.invalidate_recordset(["message_error", "message_info"])
            self.assertEqual(self.social_post_id.message_error, "Refused")
            self.assertEqual(self.social_post_id.message_info, "Changed")
            self.assertEqual(mock_errors.call_count, 1)

    def test_post_check_messages_keep_their_order(self):
        """The block must not reshuffle itself between two recomputations."""
        media_beta = self.SocialMedia.create({"name": "Beta"})
        account_beta = self.SocialAccount.create(
            {"name": "Beta account", "media_id": media_beta.id}
        )
        self.social_post_id.write(
            {"account_ids": [Command.set((self.social_account_id | account_beta).ids)]}
        )

        def one_message_per_media(post, media_type, account=None):
            return [f"{media_type} refuses this post"]

        with self._fake_media_types(
            alpha=self.social_media_id, beta=media_beta
        ), patch.object(
            type(self.social_post_id),
            "_get_post_errors",
            autospec=True,
            side_effect=one_message_per_media,
        ):
            messages = []
            for _unused in range(3):
                self.social_post_id.invalidate_recordset(["message_error"])
                messages.append(self.social_post_id.message_error)
        self.assertEqual(len(set(messages)), 1)
        self.assertEqual(messages[0], "alpha refuses this post\nbeta refuses this post")

    def test_post_check_messages_skip_a_media_without_type(self):
        """A social media with no connector behind it is nothing to ask about.

        Its ``media_type`` is ``False``, which cannot even be sorted next to
        the string of a connector, so it never reaches the hooks.
        """
        media_beta = self.SocialMedia.create({"name": "Beta"})
        account_beta = self.SocialAccount.create(
            {"name": "Beta account", "media_id": media_beta.id}
        )
        self.social_post_id.write(
            {"account_ids": [Command.set((self.social_account_id | account_beta).ids)]}
        )
        with self._fake_media_types(beta=media_beta), patch.object(
            type(self.social_post_id),
            "_get_post_errors",
            autospec=True,
            return_value=["Refused"],
        ) as mock_errors:
            self.social_post_id.invalidate_recordset(["message_error"])
            self.assertEqual(self.social_post_id.message_error, "Refused")
            self.assertEqual(mock_errors.call_count, 1)
            self.assertEqual(mock_errors.call_args.args[1], "beta")

    def test_post_check_messages_never_block_saving(self):
        """A post nothing can publish is still saved: it is finished later."""
        with self._fake_media_types(alpha=self.social_media_id), patch.object(
            type(self.social_post_id),
            "_get_post_errors",
            autospec=True,
            return_value=["Refused"],
        ):
            self.social_post_id.write({"message": "Still a draft"})
            self.assertEqual(self.social_post_id.message, "Still a draft")
            self.assertEqual(self.social_post_id.message_error, "Refused")

    def test_check_publishable_raises_what_the_form_shows(self):
        """The publication and the form read the same hook, with the account."""
        with self._fake_media_types(alpha=self.social_media_id), patch.object(
            type(self.social_post_id),
            "_get_post_errors",
            autospec=True,
            return_value=["Refused", "And also refused"],
        ) as mock_errors:
            with self.assertRaises(UserError) as error:
                self.social_post_account_id._check_publishable()
            self.assertEqual(
                mock_errors.call_args.kwargs["account"], self.social_account_id
            )
        self.assertEqual(str(error.exception), "Refused\nAnd also refused")

    def test_check_publishable_says_nothing_about_the_warnings(self):
        """A warning never stops a publication, so it is not read here."""
        with self._fake_media_types(alpha=self.social_media_id), patch.object(
            type(self.social_post_id),
            "_get_post_warnings",
            autospec=True,
            return_value=["Changed"],
        ) as mock_warnings:
            self.social_post_account_id._check_publishable()
        mock_warnings.assert_not_called()

    def test_get_checked_message_answers_the_post_by_default(self):
        """The form asks about the post, so it reads what the user is writing."""
        self.assertEqual(
            self.social_post_id._get_checked_message(), self.social_post_id.message
        )

    def test_check_publishable_measures_the_message_that_is_published(self):
        """The rules count what goes out, not what the post was written with.

        A publication promoting a marketing campaign has its links replaced
        by tracked ones, and a tracked link is longer than the short one it
        replaces, so a message inside the limit of the social media while it
        is written can be over it by the time it is sent. The rule is faked
        because base declares no limit of its own: what is under test is
        which of the two strings the rules are handed.
        """
        written = "Read https://oca.io"
        limit = len(written)
        campaign = self.env["utm.campaign"].create({"name": "Tracked links"})
        self.social_post_id.write({"message": written, "campaign_id": campaign.id})
        post_account = self.social_post_account_id
        post_account.write({"message": written})
        post_account._shorten_message_links()
        self.assertGreater(
            len(post_account.message),
            limit,
            msg="The tracked link has to be longer than the one written, or "
            "there is nothing here for the check to catch.",
        )

        def refuse_a_message_over_the_limit(post, media_type, account=None):
            message = post._get_checked_message()
            if len(message) <= limit:
                return []
            return [f"{len(message)} characters is over the limit of {limit}."]

        with self._fake_media_types(alpha=self.social_media_id), patch.object(
            type(self.social_post_id),
            "_get_post_errors",
            autospec=True,
            side_effect=refuse_a_message_over_the_limit,
        ):
            self.social_post_id.invalidate_recordset(["message_error"])
            self.assertFalse(
                self.social_post_id.message_error,
                msg="The post as it is written fits, so the banner of the "
                "form has nothing to say.",
            )
            with self.assertRaises(UserError) as error:
                post_account._check_publishable()
        self.assertIn("over the limit", str(error.exception))

    def test_post_preview_names_the_videos(self):
        """A post carrying only a video used to preview no media at all."""
        video = self.env["ir.attachment"].create(
            {
                "name": "holidays.mp4",
                "type": "binary",
                "datas": self.video_data,
            }
        )
        self.social_post_id.write({"video_ids": [Command.set(video.ids)]})
        self.assertIn("holidays.mp4", self.social_post_id.post_preview)

    def test_post_preview_counts_the_medias_it_does_not_draw(self):
        """The card draws two medias, so it has to say how many are left."""
        Attachment = self.env["ir.attachment"]
        images = Attachment.create(
            [
                {"name": f"image_{number}.png", "datas": self.image_base64}
                for number in range(3)
            ]
        )
        videos = Attachment.create(
            [
                {"name": f"video_{number}.mp4", "datas": self.video_data}
                for number in range(4)
            ]
        )
        post = self.social_post_id
        post.write(
            {
                "image_ids": [Command.set(images.ids)],
                "video_ids": [Command.set(videos.ids)],
            }
        )
        preview = post.post_preview
        self.assertIn("+1", preview)
        self.assertIn("+2", preview)
        self.assertIn("video_0.mp4", preview)
        self.assertNotIn("video_2.mp4", preview)

    def test_image_urls_carry_the_checksum_of_the_attachment(self):
        """The URL changes with the image so the browser may cache it."""
        image = self.env["ir.attachment"].create(
            {"name": "image.png", "datas": self.image_base64}
        )
        self.social_post_id.write({"image_ids": [Command.set(image.ids)]})
        self.assertEqual(
            json.loads(self.social_post_id.image_urls),
            [f"/web/image/{image.id}-{image.checksum}"],
        )

    def test_video_urls_follow_the_upload_order(self):
        """The videos are served by ``/web/content``, ordered as they came."""
        videos = self.env["ir.attachment"].create(
            [
                {"name": f"video_{number}.mp4", "datas": self.video_data}
                for number in range(2)
            ]
        )
        post = self.social_post_id
        post.write({"video_ids": [Command.set(videos.ids)]})
        # Read back from database: ``ir.attachment`` is ordered ``id desc``,
        # and the gallery is not.
        post.invalidate_recordset()
        self.assertEqual(
            json.loads(post.video_urls),
            [f"/web/content/{video.id}?unique={video.checksum}" for video in videos],
        )

    def test_video_urls_of_a_post_without_videos(self):
        """A post with no video answers an empty gallery, not ``False``."""
        self.assertEqual(json.loads(self.social_post_id.video_urls), [])

    def test_video_urls_are_recomputed_when_the_video_changes(self):
        video = self.env["ir.attachment"].create(
            {"name": "video.mp4", "datas": self.video_data}
        )
        self.social_post_id.write({"video_ids": [Command.set(video.ids)]})
        before = self.social_post_id.video_urls
        video.write({"datas": self.image_base64})
        self.assertNotEqual(self.social_post_id.video_urls, before)

    def test_image_urls_are_recomputed_when_the_image_changes(self):
        image = self.env["ir.attachment"].create(
            {"name": "image.png", "datas": self.image_base64}
        )
        self.social_post_id.write({"image_ids": [Command.set(image.ids)]})
        before = self.social_post_id.image_urls
        image.write({"datas": self.video_data})
        self.assertNotEqual(self.social_post_id.image_urls, before)

    def test_post_preview_says_nothing_when_everything_is_drawn(self):
        image = self.env["ir.attachment"].create(
            {"name": "image.png", "datas": self.image_base64}
        )
        self.social_post_id.write({"image_ids": [Command.set(image.ids)]})
        self.assertNotIn("+", self.social_post_id.post_preview)

    def test_post_preview_keeps_the_line_breaks(self):
        """The social media publishes the paragraphs, so the preview draws them.

        The block is what carries the ``white-space``, the same one the cards
        use, so the line breaks are looked for inside it.
        """
        self.social_post_id.message = "First line\nSecond line"
        self.assertIn(
            '<div class="o_social_message">First line\nSecond line</div>',
            self.social_post_id.post_preview,
        )

    def test_post_preview_offers_the_link_that_unfolds_the_message(self):
        """The preview cuts the message, so it carries the link showing it whole.

        The link is drawn hidden: whether the message really does not fit
        depends on the width the preview ends up with, which only the widget
        of the field can measure.
        """
        preview = self.social_post_id.post_preview
        self.assertIn("show-more-message", preview)
        self.assertIn("d-none", preview)

    def test_post_preview_escapes_the_message(self):
        """The message is plain text: it never becomes markup."""
        self.social_post_id.message = "<b>bold</b>"
        preview = self.social_post_id.post_preview
        self.assertIn("&lt;b&gt;bold&lt;/b&gt;", preview)
        self.assertNotIn("<b>bold</b>", preview)

    def test_post_preview_serves_the_media_icon_from_web_image(self):
        """The icon of a social media is a field, not a file of the connector."""
        self.social_media_id.image = self.image_base64
        preview = self.social_post_id._render_template_preview()
        self.assertIn(
            f"/web/image/social.media/{self.social_media_id.id}/image", preview
        )
        self.assertNotIn("static/img", preview)

    def test_post_preview_hides_the_icon_when_the_media_has_no_image(self):
        self.assertNotIn(
            "/web/image/social.media/", self.social_post_id._render_template_preview()
        )

    def test_post_preview_escapes_the_author_name(self):
        self.social_media_id.name = "<b>Ev&il</b>"
        preview = self.social_post_id._render_template_preview()
        self.assertIn("&lt;b&gt;Ev&amp;il&lt;/b&gt;", preview)
        self.assertNotIn("<b>Ev", preview)

    def test_post_preview_escapes_the_video_name(self):
        video = self.env["ir.attachment"].create(
            {
                "name": "<script>alert(1)</script>.mp4",
                "type": "binary",
                "datas": self.video_data,
            }
        )
        self.social_post_id.write({"video_ids": [Command.set(video.ids)]})
        preview = self.social_post_id.post_preview
        self.assertIn("&lt;script&gt;", preview)
        self.assertNotIn("<script>", preview)

    def test_image_urls_follow_the_upload_order(self):
        """``ir.attachment`` is ordered ``id desc``, the gallery is not."""
        images = self.env["ir.attachment"].create(
            [
                {"name": f"image_{number}.png", "datas": self.image_base64}
                for number in range(3)
            ]
        )
        post = self.social_post_id
        post.write({"image_ids": [Command.set(images.ids)]})
        # The cache holds the order of the write command, so the images have
        # to be read back from database for the order to be the one of the
        # publications the cron sends.
        post.invalidate_recordset()
        post._compute_image_urls()
        self.assertEqual(
            json.loads(post.image_urls),
            [f"/web/image/{image.id}-{image.checksum}" for image in images],
        )

    def test_post_preview_draws_the_images_in_upload_order(self):
        """The preview drops the last images added, never the first ones."""
        images = self.env["ir.attachment"].create(
            [
                {"name": f"image_{number}.png", "datas": self.image_base64}
                for number in range(3)
            ]
        )
        post = self.social_post_id
        post.write({"image_ids": [Command.set(images.ids)]})
        post.invalidate_recordset()
        preview = post._render_template_preview()
        self.assertIn(f"/web/image/{images[0].id}", preview)
        self.assertIn(f"/web/image/{images[1].id}", preview)
        self.assertNotIn(f"/web/image/{images[2].id}", preview)

    def test_post_preview_draws_the_medias_not_saved_yet(self):
        """The preview is rendered on every onchange, before the post exists.

        The medias carry a ``NewId`` there, which cannot be compared, so
        ordering them by identifier used to break the whole form.
        """
        post = self.SocialPost.new(
            {
                "message": "Test message",
                "account_ids": [Command.set(self.social_account_id.ids)],
            }
        )
        stored = self.env["ir.attachment"].create(
            {"name": "stored.png", "datas": self.image_base64}
        )
        post.image_ids = stored + self.env["ir.attachment"].new(
            {"name": "just_added.png", "datas": self.image_base64}
        )
        images, _videos = post._medias_for_publication()
        self.assertEqual(images.mapped("name"), ["stored.png", "just_added.png"])
        self.assertIn("Test message", post._render_template_preview())

    def test_check_media_kind_rejects_a_video_in_the_images(self):
        """The accepted extensions of the dialog do not stop a drag and drop."""
        video = self.env["ir.attachment"].create(
            {"name": "holidays.mp4", "datas": self.video_data}
        )
        with self.assertRaises(ValidationError):
            self.social_post_id.write({"image_ids": [Command.set(video.ids)]})

    def test_check_media_kind_rejects_an_image_in_the_videos(self):
        image = self.env["ir.attachment"].create(
            {"name": "image.png", "datas": self.image_base64}
        )
        with self.assertRaises(ValidationError):
            self.social_post_id.write({"video_ids": [Command.set(image.ids)]})

    def test_check_media_kind_accepts_any_image_format(self):
        """The base knows no social media, so it refuses no image format."""
        images = self.env["ir.attachment"].create(
            [
                {"name": "animation.gif", "datas": self.image_base64},
                {"name": "picture.webp", "datas": self.image_base64},
            ]
        )
        self.social_post_id.write({"image_ids": [Command.set(images.ids)]})
        self.assertEqual(self.social_post_id.image_ids, images)

    def test_post_preview_values_are_rendered_per_media(self):
        """The hook receives the media, so a connector only touches its own."""
        other_media = self.SocialMedia.create({"name": "Other"})
        other_account = self.SocialAccount.create(
            {"name": "Other account", "media_id": other_media.id}
        )
        post = self.SocialPost.create(
            {
                "message": "Test message",
                "account_ids": [
                    Command.set((self.social_account_id + other_account).ids)
                ],
            }
        )
        medias = []
        with patch.object(
            type(post),
            "_render_values_preview",
            autospec=True,
            side_effect=lambda post, media: medias.append(media) or {},
        ):
            post._render_template_preview()
        self.assertEqual(medias, list(post.account_ids.media_id))

    def test_post_preview_groups_the_accounts_of_one_media(self):
        """Accounts of the same media share a single preview card."""
        media = self.SocialMedia.create({"name": "Bulletin"})
        accounts = self.SocialAccount.create(
            [
                {"name": "Corporate desk", "media_id": media.id},
                {"name": "Developer desk", "media_id": media.id},
            ]
        )
        post = self.SocialPost.create(
            {
                "message": "Test message",
                "account_ids": [Command.set(accounts.ids)],
            }
        )
        self.assertEqual(post.post_preview.count("Bulletin"), 1)
        for account in accounts:
            self.assertNotIn(account.name, post.post_preview)

    def test_unlink_post_takes_its_publications_with_it(self):
        """A publication that never reached the social media holds nothing back."""
        post = self.social_post_id
        line = self.social_post_account_id
        line.write({"state": "failed", "remote_ref": False})
        post.unlink()
        self.assertFalse(post.exists())
        self.assertFalse(line.exists())

    def test_unlink_post_refuses_while_it_is_online(self):
        post = self.social_post_id
        self.social_post_account_id.write(
            {"state": "posted", "remote_ref": "urn:li:share:9"}
        )
        with self.assertRaises(UserError) as error:
            post.unlink()
        self.assertIn("still published on", str(error.exception))
        self.assertIn(self.social_account_id.display_name, str(error.exception))
        self.assertTrue(post.exists())
        self.assertTrue(self.social_post_account_id.exists())

    def test_unlink_post_deleted_on_the_social_media(self):
        """A publication gone from the social media is only history."""
        post = self.social_post_id
        line = self.social_post_account_id
        line.write({"state": "deleted", "remote_ref": "urn:li:share:9"})
        post.unlink()
        self.assertFalse(post.exists())
        self.assertFalse(line.exists())

    def test_unlink_post_reaches_the_archived_publications(self):
        post = self.social_post_id
        line = self.social_post_account_id
        post.write({"active": False})
        self.assertFalse(line.active)
        post.unlink()
        self.assertFalse(line.exists())

    def test_unlink_post_takes_its_medias_with_it(self):
        """A deleted post leaves no attachment pointing at a gone record.

        The medias of a post are attached to it, so ``unlink`` takes them
        along and the filestore frees the files on its next collection.
        """
        post = self.social_post_id
        line = self.social_post_account_id
        line.write({"state": "failed", "remote_ref": False})
        image = self.env["ir.attachment"].create(
            {"name": "deleted_image.png", "datas": self.image_base64}
        )
        video = self.env["ir.attachment"].create(
            {"name": "deleted_video.mp4", "datas": self.video_data}
        )
        post.write(
            {
                "image_ids": [Command.set(image.ids)],
                "video_ids": [Command.set(video.ids)],
            }
        )
        self.assertEqual(image.res_model, "social.post")
        self.assertEqual(image.res_id, post.id)
        post.unlink()
        self.assertFalse(image.exists())
        self.assertFalse(video.exists())

    def test_unlink_post_takes_the_medias_of_its_publications_with_it(self):
        """What the publication downloaded is deleted with the publication."""
        post = self.social_post_id
        line = self.social_post_account_id
        line.write({"state": "failed", "remote_ref": False})
        downloaded = self.env["ir.attachment"].create(
            {
                "name": "downloaded_image.png",
                "datas": self.image_base64,
                "res_model": "social.post.account",
                "res_id": line.id,
            }
        )
        line.write({"image_ids": [Command.set(downloaded.ids)]})
        post.unlink()
        self.assertFalse(downloaded.exists())

    def test_unlink_post_keeps_the_medias_of_another_post(self):
        """A media another post still carries is attached to that one."""
        image = self.env["ir.attachment"].create(
            {"name": "kept_image.png", "datas": self.image_base64}
        )
        keeper = self.SocialPost.create(
            {
                "message": "The post that keeps the image",
                "account_ids": [Command.set(self.social_account_id.ids)],
                "image_ids": [Command.set(image.ids)],
            }
        )
        deleted = self.SocialPost.create(
            {
                "message": "The post that is deleted",
                "account_ids": [Command.set(self.social_account_id.ids)],
                "image_ids": [Command.set(image.ids)],
            }
        )
        self.assertEqual(image.res_id, keeper.id)
        deleted.unlink()
        self.assertTrue(image.exists())
        self.assertEqual(keeper.image_ids, image)

    def test_dashboard_shows_only_what_exists_on_the_social_media(self):
        action = self.env.ref("social_media_base.social_post_account_action")
        self.assertEqual(literal_eval(action.domain), [("remote_ref", "!=", False)])

    def test_count_post_impression_uses_impression_count(self):
        self.social_post_account_id.write({"impression_count": 7, "engagement": 3.5})
        self.assertEqual(self.social_post_id.count_post_impression, 7)
        self.assertEqual(self.social_post_id.count_post_engagement, 3.5)

    def test_interactions_count_adds_the_statistics_of_the_publication(self):
        self.social_post_account_id.write(
            {
                "click_count": 4,
                "like_count": 3,
                "comment_count": 2,
                "share_count": 1,
            }
        )
        self.assertEqual(self.social_post_account_id.interactions_count, 10)
        self.assertEqual(self.social_post_id.count_post_interactions, 10)

    def test_effective_date_is_the_scheduled_date_until_it_is_published(self):
        post = self._create_scheduled_post(minutes=30)
        post_account = self.SocialPostAccount.create(
            {
                "post_id": post.id,
                "account_id": self.social_account_id.id,
                "message": "Scheduled message",
            }
        )
        self.assertEqual(post_account.effective_date, post.send_post_date)
        self.assertTrue(post_account.is_scheduled)

        published_date = fields.Datetime.now()
        post_account.published_date = published_date
        self.assertEqual(post_account.effective_date, published_date)
        self.assertFalse(post_account.is_scheduled)

    def test_effective_date_of_a_publication_without_post(self):
        post_account = self.SocialPostAccount.create(
            {
                "account_id": self.social_account_id.id,
                "message": "Imported publication",
            }
        )
        self.assertFalse(post_account.effective_date)
        self.assertFalse(post_account.is_scheduled)

    def test_media_attachments_are_anchored_to_the_publication(self):
        attachment = self.env["ir.attachment"].create(
            {
                "name": "urn:li:digitalmediaAsset:TEST",
                "type": "binary",
                "res_model": "social.post.account",
                "datas": b"ZmFrZS1pbWFnZQ==",
            }
        )
        self.assertFalse(attachment.res_id)
        post_account = self.SocialPostAccount.create(
            {
                "message": "With an image",
                "account_id": self.social_account_id.id,
                "image_ids": [Command.set(attachment.ids)],
            }
        )
        self.assertEqual(
            (attachment.res_model, attachment.res_id),
            ("social.post.account", post_account.id),
            "The attachment must point at its publication, otherwise only "
            "the system administrators can read it",
        )

    def test_media_attachments_anchored_on_write(self):
        post_account = self.SocialPostAccount.create(
            {
                "message": "Without an image yet",
                "account_id": self.social_account_id.id,
            }
        )
        attachment = self.env["ir.attachment"].create(
            {
                "name": "urn:li:digitalmediaAsset:TEST2",
                "type": "binary",
                "res_model": "social.post.account",
                "datas": b"ZmFrZS1pbWFnZQ==",
            }
        )
        post_account.write({"image_ids": [Command.set(attachment.ids)]})
        self.assertEqual(attachment.res_id, post_account.id)

    def test_post_media_attachments_are_anchored(self):
        attachment = self.env["ir.attachment"].create(
            {
                "name": "unsaved_post.png",
                "type": "binary",
                "res_model": "social.post",
                "datas": b"ZmFrZS1pbWFnZQ==",
            }
        )
        self.assertFalse(attachment.res_id)
        post = self.SocialPost.create(
            {
                "message": "With an image",
                "account_ids": [Command.set([self.social_account_id.id])],
                "image_ids": [Command.set(attachment.ids)],
            }
        )
        self.assertEqual(
            (attachment.res_model, attachment.res_id),
            ("social.post", post.id),
            "The attachment must point at its post, otherwise only the "
            "system administrators can read it",
        )

    def test_post_media_attachments_anchored_on_write(self):
        video = self.env["ir.attachment"].create(
            {
                "name": "unsaved_post.mp4",
                "type": "binary",
                "mimetype": "video/mp4",
                "res_model": "social.post",
                "datas": b"ZmFrZS12aWRlbw==",
            }
        )
        self.social_post_id.write({"video_ids": [Command.set(video.ids)]})
        self.assertEqual(video.res_id, self.social_post_id.id)

    def test_post_media_attachments_keep_their_owner(self):
        """Anchoring never steals an attachment that already has one."""
        attachment = self.env["ir.attachment"].create(
            {
                "name": "owned.png",
                "type": "binary",
                "res_model": "social.post.account",
                "res_id": self.social_post_account_id.id,
                "datas": b"ZmFrZS1pbWFnZQ==",
            }
        )
        self.social_post_id.write({"image_ids": [Command.set(attachment.ids)]})
        self.assertEqual(
            (attachment.res_model, attachment.res_id),
            ("social.post.account", self.social_post_account_id.id),
        )

    def test_removing_a_media_from_a_post_releases_it(self):
        """A media the post stops carrying goes back to belonging to nobody.

        The upload widget only forgets the link, so without this the file
        would stay in the filestore until the post itself is deleted. The
        attachment is not deleted here: the vacuum does it a day later.
        """
        post = self.social_post_id
        video = self.env["ir.attachment"].create(
            {"name": "removed_video.mp4", "datas": self.video_data}
        )
        post.write({"video_ids": [Command.set(video.ids)]})
        self.assertEqual(video.res_id, post.id)
        post.write({"video_ids": [Command.clear()]})
        self.assertFalse(video.res_id)
        self._age_attachments(video)
        self.SocialPost._gc_lost_media_attachments()
        self.assertFalse(video.exists())

    def test_removing_a_media_a_publication_still_carries_keeps_it(self):
        """The publications of a post point at the very medias of the post."""
        post = self.social_post_id
        line = self.social_post_account_id
        image = self.env["ir.attachment"].create(
            {"name": "shared_image.png", "datas": self.image_base64}
        )
        post.write({"image_ids": [Command.set(image.ids)]})
        line.write({"image_ids": [Command.set(image.ids)]})
        post.write({"image_ids": [Command.clear()]})
        self.assertEqual(image.res_id, post.id)
        self.assertEqual(line.image_ids, image)

    def test_removing_a_media_the_post_does_not_own_keeps_it(self):
        """Only the record a media is anchored to answers for it."""
        post = self.social_post_id
        downloaded = self.env["ir.attachment"].create(
            {
                "name": "downloaded_image.png",
                "datas": self.image_base64,
                "res_model": "social.post.account",
                "res_id": self.social_post_account_id.id,
            }
        )
        post.write({"image_ids": [Command.set(downloaded.ids)]})
        post.write({"image_ids": [Command.clear()]})
        self.assertEqual(downloaded.res_id, self.social_post_account_id.id)

    def test_removing_a_media_leaves_the_chatter_attachments_alone(self):
        """A file of the chatter is not a media of the post."""
        post = self.social_post_id
        attached = self.env["ir.attachment"].create(
            {
                "name": "chatter_file.txt",
                "datas": self.image_base64,
                "res_model": "social.post",
                "res_id": post.id,
            }
        )
        image = self.env["ir.attachment"].create(
            {"name": "removed_image.png", "datas": self.image_base64}
        )
        post.write({"image_ids": [Command.set(image.ids)]})
        post.write({"image_ids": [Command.clear()]})
        self.assertFalse(image.res_id)
        self.assertEqual(attached.res_id, post.id)

    def test_removing_a_downloaded_media_from_a_publication_releases_it(self):
        """A publication answers for what it downloaded from the social media."""
        line = self.social_post_account_id
        downloaded = self.env["ir.attachment"].create(
            {
                "name": "downloaded_image.png",
                "datas": self.image_base64,
                "res_model": "social.post.account",
            }
        )
        line.write({"image_ids": [Command.set(downloaded.ids)]})
        self.assertEqual(downloaded.res_id, line.id)
        line.write({"image_ids": [Command.clear()]})
        self.assertFalse(downloaded.res_id)
        self._age_attachments(downloaded)
        self.SocialPostAccount._gc_lost_media_attachments()
        self.assertFalse(downloaded.exists())

    def test_removing_a_media_of_the_post_from_a_publication_keeps_it(self):
        """What a publication shares with its post belongs to the post."""
        post = self.social_post_id
        line = self.social_post_account_id
        image = self.env["ir.attachment"].create(
            {"name": "post_image.png", "datas": self.image_base64}
        )
        post.write({"image_ids": [Command.set(image.ids)]})
        line.write({"image_ids": [Command.set(image.ids)]})
        line.write({"image_ids": [Command.clear()]})
        self.assertEqual(image.res_id, post.id)
        self.assertEqual(post.image_ids, image)

    def _age_attachments(self, attachments, days=2):
        """Move the dates of the attachments back, as the vacuum reads them."""
        older = fields.Datetime.subtract(fields.Datetime.now(), days=days)
        # The dates are written in SQL, so what the ORM still holds for these
        # attachments has to reach the database first and be forgotten after,
        # or the next flush would write ``write_date`` back to now.
        self.env.flush_all()
        self.env.cr.execute(
            "UPDATE ir_attachment SET create_date = %s, write_date = %s "
            "WHERE id IN %s",
            (older, older, tuple(attachments.ids)),
        )
        attachments.invalidate_recordset(["create_date", "write_date"])

    def test_gc_lost_media_attachments_deletes_what_a_form_never_saved(self):
        """A file uploaded to a post that was never saved has no owner.

        The widget stores it with ``res_id`` 0, so no record carries it and
        no record will ever delete it.
        """
        lost = self.env["ir.attachment"].create(
            {
                "name": "unsaved_video.mp4",
                "datas": self.video_data,
                "res_model": "social.post",
                "res_id": 0,
            }
        )
        self._age_attachments(lost)
        self.SocialPost._gc_lost_media_attachments()
        self.assertFalse(lost.exists())

    def test_gc_lost_media_attachments_keeps_a_form_still_open(self):
        """The day of margin is the form the user has not saved yet."""
        pending = self.env["ir.attachment"].create(
            {
                "name": "pending_video.mp4",
                "datas": self.video_data,
                "res_model": "social.post",
                "res_id": 0,
            }
        )
        self.SocialPost._gc_lost_media_attachments()
        self.assertTrue(pending.exists())

    def test_gc_lost_media_attachments_keeps_the_medias_of_a_post(self):
        """An anchored media is old on purpose: it is the post that is old."""
        image = self.env["ir.attachment"].create(
            {"name": "old_image.png", "datas": self.image_base64}
        )
        self.social_post_id.write({"image_ids": [Command.set(image.ids)]})
        self._age_attachments(image)
        self.SocialPost._gc_lost_media_attachments()
        self.assertTrue(image.exists())

    def test_gc_lost_media_attachments_keeps_what_a_record_carries(self):
        """The vacuum never deletes a media under the record showing it.

        Nothing releases a media another record carries, and the many2many is
        ``ondelete="restrict"``, so this is what keeps the vacuum from failing
        on an attachment that reached ``res_id`` 0 with a holder left.
        """
        image = self.env["ir.attachment"].create(
            {
                "name": "carried_image.png",
                "datas": self.image_base64,
                "res_model": "social.post",
                "res_id": 0,
            }
        )
        self.social_post_id.write({"image_ids": [Command.link(image.id)]})
        image.sudo().write({"res_id": 0})
        self._age_attachments(image)
        self.SocialPost._gc_lost_media_attachments()
        self.assertTrue(image.exists())

    def test_media_refs_of_a_new_publication_is_empty(self):
        """An empty ``fields.Json`` is stored as ``NULL`` and read as ``False``.

        ``convert_to_cache`` turns any falsy value into ``None`` and
        ``convert_to_record`` turns it back into ``False``, so the field never
        reads as ``{}``. Everything that reads it does ``media_refs or {}``.
        """
        post_account = self.SocialPostAccount.create(
            {
                "message": "Nothing published yet",
                "account_id": self.social_account_id.id,
            }
        )
        self.assertFalse(post_account.media_refs)
        self.assertEqual(post_account.media_refs or {}, {})

    def _create_publication_images(self, count=1, post_account=None):
        """Attach ``count`` images to a publication and return them.

        ``_check_media_refs`` answers for the medias the publication holds,
        so every reference a test writes needs an attachment of its own.

        :rtype: odoo.api.Model
        """
        images = self.env["ir.attachment"].create(
            [
                {"name": f"media_{index}.png", "type": "binary", "datas": b"aW1n"}
                for index in range(count)
            ]
        )
        (post_account or self.social_post_account_id).write(
            {"image_ids": [Command.link(image.id) for image in images]}
        )
        return images

    def test_media_refs_is_written_by_reassigning_it(self):
        """``fields.Json`` does not track mutations, only assignments.

        The value is read back after invalidating the cache, so that what the
        test checks is what reached the database and not what the ORM still
        holds in memory.
        """
        post_account = self.social_post_account_id
        first, second = self._create_publication_images(count=2)
        post_account.media_refs = {str(first.id): "urn:li:image:FIRST"}
        post_account.media_refs = {
            **post_account.media_refs,
            str(second.id): "urn:li:image:SECOND",
        }
        post_account.invalidate_recordset(["media_refs"])
        self.assertEqual(
            post_account.media_refs,
            {
                str(first.id): "urn:li:image:FIRST",
                str(second.id): "urn:li:image:SECOND",
            },
        )

    def test_media_refs_keys_are_strings(self):
        """An ``int`` key comes back as a string, so nothing looks it up."""
        post_account = self.social_post_account_id
        image = self._create_publication_images()
        post_account.media_refs = {image.id: "urn:li:image:FIRST"}
        post_account.invalidate_recordset(["media_refs"])
        self.assertEqual(list(post_account.media_refs), [str(image.id)])
        self.assertFalse(post_account.media_refs.get(image.id))

    def test_check_media_refs_refuses_the_same_media_twice(self):
        """One media of the social media is stored on one attachment."""
        post_account = self.social_post_account_id
        images = self._create_publication_images(count=2)
        with self.assertRaises(ValidationError):
            post_account.media_refs = {
                str(image.id): "urn:li:image:SAME" for image in images
            }

    def test_check_media_refs_refuses_a_reference_without_media(self):
        """A reference to the media of another publication is refused.

        The attachment is anchored somewhere else, so the reference makes
        this publication answer for a media it does not have. That is what
        the constraint watches.
        """
        post_account = self.social_post_account_id
        other = self.SocialPostAccount.create(
            {
                "message": "Published somewhere else",
                "account_id": self.social_account_id.id,
            }
        )
        stored = self._create_publication_images()
        foreign = self._create_publication_images(post_account=other)
        with self.assertRaises(ValidationError):
            post_account.media_refs = {
                str(stored.id): "urn:li:image:STORED",
                str(foreign.id): "urn:li:image:FOREIGN",
            }

    def test_check_media_refs_allows_a_reference_whose_media_was_released(self):
        """A reference to a media nobody owns any more is left alone.

        It is what the retention of the downloaded medias writes: the
        attachment is released so the vacuum frees the file, and the
        reference stays so the next synchronization pass knows the
        publication already had that media and does not download it again.
        """
        post_account = self.social_post_account_id
        stored, released = self._create_publication_images(count=2)
        post_account.media_refs = {
            str(stored.id): "urn:li:image:STORED",
            str(released.id): "urn:li:image:RELEASED",
        }
        post_account.write({"image_ids": [Command.unlink(released.id)]})
        self.assertEqual(released.sudo().res_id, 0)
        post_account.invalidate_recordset(["media_refs"])
        self.assertEqual(
            post_account.media_refs,
            {
                str(stored.id): "urn:li:image:STORED",
                str(released.id): "urn:li:image:RELEASED",
            },
        )

    def test_check_media_refs_allows_a_reference_whose_media_is_gone(self):
        """A reference left without its attachment points nowhere.

        It is the trace the retention of the downloaded medias leaves behind:
        the attachment is released so the disk is freed, and the reference
        stays so the next synchronization pass knows the publication already
        had that media and does not download it again.
        """
        post_account = self.social_post_account_id
        stored, released = self._create_publication_images(count=2)
        released_id = released.id
        post_account.write({"image_ids": [Command.unlink(released_id)]})
        released.sudo().unlink()
        post_account.media_refs = {
            str(stored.id): "urn:li:image:STORED",
            str(released_id): "urn:li:image:RELEASED",
        }
        post_account.invalidate_recordset(["media_refs"])
        self.assertEqual(
            post_account.media_refs,
            {
                str(stored.id): "urn:li:image:STORED",
                str(released_id): "urn:li:image:RELEASED",
            },
        )

    def test_check_media_refs_allows_the_medias_attached_by_hand(self):
        """A publication with medias and no reference is what the user made."""
        post_account = self.social_post_account_id
        images = self._create_publication_images(count=2)
        post_account.invalidate_recordset(["media_refs"])
        self.assertEqual(post_account.image_ids, images)
        self.assertFalse(post_account.media_refs)

    def test_the_fan_out_shares_the_medias_of_the_post(self):
        """Publishing on two accounts stores one image once."""
        Attachment = self.env["ir.attachment"]
        images = Attachment.create(
            [
                {"name": f"shared_{index}.png", "type": "binary", "datas": b"aW1n"}
                for index in range(2)
            ]
        )
        video = Attachment.create(
            {"name": "shared.mp4", "type": "binary", "datas": b"dmlk"}
        )
        post = self.SocialPost.create(
            {
                "message": "Shared medias",
                "account_ids": [
                    Command.set((self.social_account_id | self.other_account_id).ids)
                ],
                "image_ids": [Command.set(images.ids)],
                "video_ids": [Command.set(video.ids)],
            }
        )
        before = Attachment.search_count([])
        with patch.object(
            type(self.social_post_account_id), "_action_post", autospec=True
        ):
            post.action_create_post_account()
        lines = post.post_account_ids
        self.assertEqual(len(lines), 2)
        for line in lines:
            self.assertEqual(line.image_ids, images)
            self.assertEqual(line.video_ids, video)
        self.assertEqual(
            Attachment.search_count([]),
            before,
            "Sharing the attachments of the post must not create a copy",
        )

    def test_anchoring_leaves_the_medias_of_the_post_to_the_post(self):
        """Anchoring a publication never claims what the post shares.

        The post anchors its own attachments, so a shared one normally
        arrives with a ``res_id`` already. This checks the guard itself, on
        an attachment that reaches the publication without one.
        """
        image = self.env["ir.attachment"].create(
            {"name": "owned_by_the_post.png", "type": "binary", "datas": b"aW1n"}
        )
        post = self.SocialPost.create(
            {
                "message": "One image, one account",
                "account_ids": [Command.set([self.social_account_id.id])],
                "image_ids": [Command.set(image.ids)],
            }
        )
        image.sudo().write({"res_model": "social.post", "res_id": False})
        post_account = self.SocialPostAccount.create(
            {
                "message": post.message,
                "account_id": self.social_account_id.id,
                "post_id": post.id,
                "image_ids": [Command.set(image.ids)],
            }
        )
        self.assertEqual(
            (image.res_model, image.res_id),
            ("social.post", False),
            "The publication must not claim an attachment of its post",
        )
        self.assertEqual(post_account.image_ids, image)

    def test_filter_by_media_types(self):
        with patch(
            "odoo.models.BaseModel.search",
            autospec=True,
            return_value=self.social_post_account_id,
        ) as mock_search:
            result = self.social_post_id._filter_by_media_types([])
            self.assertEqual(len(result), 1)
            mock_search.assert_called_once()

    def test_filter_by_media_types_needs_a_single_post(self):
        with self.assertRaises(ValueError):
            self.SocialPost._filter_by_media_types([])

    def test_get_media_types_domain(self):
        """The domain a connector overrides to reach other publications."""
        self.assertEqual(
            self.social_post_id._get_media_types_domain(["linkedin"]),
            [
                ("media_type", "in", ["linkedin"]),
                ("post_id", "=", self.social_post_id.id),
                ("state", "in", ("ready", "failed")),
            ],
        )

    def test_action_cancel(self):
        self.social_post_id.action_cancel()
        self.assertEqual(self.social_post_id.state, "cancelled")
        post_id = self.SocialPost.create(
            {
                "message": "Test",
                "account_ids": [Command.set([self.social_account_id.id])],
                "state": "publishing",
            }
        )
        with self.assertRaises(UserError):
            post_id.action_cancel()
        post_id.state = "partially_published"
        with self.assertRaises(UserError):
            post_id.action_cancel()

    def test_prepare_post_account_values(self):
        self.social_post_id.write(
            {"account_ids": [Command.link(self.other_account_id.id)]}
        )
        result = self.social_post_id._prepare_post_account_values()
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0][2]["account_id"], self.other_account_id.id)


@tagged("post_install", "-at_install")
class TestSocialPostBaseUsers(TestSocialMediaBaseCommon):
    """Users are created here, so every module has to be in the registry."""

    def test_partial_publication_notifies_the_responsible_of_the_account(self):
        """The user notified is the one in charge of the account that failed."""
        other_user = self.env["res.users"].create(
            {
                "name": "Other responsible",
                "login": "other_responsible_test",
                "groups_id": [
                    Command.set(
                        [
                            self.env.ref("base.group_user").id,
                            self.env.ref(
                                "social_media_base.group_social_media_user"
                            ).id,
                        ]
                    )
                ],
            }
        )
        failing_account = self.SocialAccount.create(
            {
                "name": "Linkedin of another user",
                "media_id": self.social_media_id.id,
                "user_id": other_user.id,
                "username": "other_responsible_account",
            }
        )
        post = self.SocialPost.create(
            {
                "message": "Message published only in part",
                "account_ids": [
                    Command.set((self.social_account_id | failing_account).ids)
                ],
            }
        )

        def fake_action_post(records, post_id=None):
            for line in post_id.post_account_ids:
                if line.account_id == failing_account:
                    line.write({"state": "failed"})
                else:
                    line.write({"state": "posted", "remote_ref": "urn:posted"})

        with patch.object(
            type(self.social_post_account_id),
            "_action_post",
            autospec=True,
            side_effect=fake_action_post,
        ):
            post._action_create_post_account()
        self.assertEqual(post.state, "partially_published")
        notification = post.message_ids.filtered(
            lambda message: "failed on" in (message.body or "")
        )
        self.assertEqual(notification.partner_ids, other_user.partner_id)

    def test_action_open_post_account_url(self):
        """The button opens the publication on the social media."""
        post_account = self.social_post_account_id
        post_account.write(
            {
                "post_account_url": "https://example.test/post/1",
                "remote_ref": "urn:li:share:open",
            }
        )
        action = post_account.action_open_post_account_url()
        self.assertEqual(action["type"], "ir.actions.act_url")
        self.assertEqual(action["url"], "https://example.test/post/1")
        self.assertEqual(action["target"], "new")

    def test_action_open_post_account_url_without_url(self):
        """A publication that never reached the social media has no address."""
        post_account = self.social_post_account_id
        post_account.write({"post_account_url": False})
        self.assertFalse(post_account.action_open_post_account_url())

    def test_action_open_post_account_url_gone(self):
        """A publication gone from the social media is not opened."""
        post_account = self.social_post_account_id
        post_account.write(
            {
                "post_account_url": "https://example.test/post/1",
                "remote_ref": "urn:li:share:gone",
                "state": "posted",
            }
        )
        with patch.object(
            type(post_account), "_check_remote_post_exists", return_value=False
        ):
            action = post_account.action_open_post_account_url()
        self.assertEqual(action["tag"], "display_notification")
        self.assertEqual(action["params"]["type"], "warning")
        self.assertEqual(action["params"]["next"]["tag"], "reload")

    def test_check_post_exists_without_remote_ref(self):
        """Without a remote reference there is nothing to look for."""
        post_account = self.social_post_account_id
        post_account.write({"remote_ref": False})
        self.assertFalse(post_account.check_post_exists())

    def test_remote_post_gone_on_action(self):
        """The publication is asked about before an action marks it gone."""
        post_account = self.social_post_account_id
        with patch.object(
            type(post_account), "_check_remote_post_exists", return_value=False
        ):
            self.assertTrue(post_account._remote_post_gone_on_action())
        with patch.object(
            type(post_account), "_check_remote_post_exists", return_value=True
        ):
            self.assertFalse(post_account._remote_post_gone_on_action())

    @mute_logger(LOGGER_POST_ACCOUNT)
    def test_remote_post_gone_on_action_unreachable(self):
        """A check that fails answers no deletion instead of raising."""
        post_account = self.social_post_account_id
        with patch.object(
            type(post_account),
            "_check_remote_post_exists",
            side_effect=ValueError("unreachable"),
        ):
            self.assertFalse(post_account._remote_post_gone_on_action())

    def _create_suspect_lines(self, count):
        """Create ``count`` published lines, each on its own account.

        A publication belongs to one account, so a batch of suspects is a line
        per account, each with the reference the social media is asked about.
        """
        lines = self.SocialPostAccount.browse()
        for index in range(count):
            account = self.SocialAccount.create(
                {
                    "name": "Linkedin batch %s" % index,
                    "media_id": self.social_media_id.id,
                    "username": "linkedin_batch_%s" % index,
                }
            )
            lines |= self.SocialPostAccount.create(
                {
                    "post_id": self.social_post_id.id,
                    "account_id": account.id,
                    "message": "Test message",
                    "remote_ref": "urn:li:share:%s" % index,
                    "post_account_url": "https://example.test/post/%s" % index,
                    "state": "posted",
                }
            )
        return lines

    def test_register_remote_post_gone_keeps_the_reference(self):
        """The reference survives the deletion: detection is not infallible."""
        post_account = self.social_post_account_id
        post_account.write(
            {
                "remote_ref": "urn:li:share:kept",
                "post_account_url": "https://example.test/post/1",
                "state": "posted",
            }
        )
        post_account._register_remote_post_gone()
        self.assertEqual(post_account.state, "deleted")
        self.assertFalse(post_account.post_account_url)
        self.assertEqual(post_account.remote_ref, "urn:li:share:kept")

    def test_check_remote_posts_exist_answers_only_the_confirmed(self):
        """The plural answers the lines the social media reported as gone."""
        lines = self._create_suspect_lines(3)
        with patch.object(
            type(lines),
            "_check_remote_post_exists",
            autospec=True,
            side_effect=lambda line: line.remote_ref != "urn:li:share:1",
        ) as check:
            self.assertEqual(lines._check_remote_posts_exist(), lines[1])
        self.assertEqual(check.call_count, 3)

    @mute_logger(LOGGER_POST_ACCOUNT)
    def test_check_remote_posts_exist_leaves_out_a_failing_check(self):
        """A check that raises confirms nothing and stops nobody else."""
        lines = self._create_suspect_lines(3)

        def check(line):
            if line.remote_ref == "urn:li:share:0":
                raise ValueError("unreachable")
            return line.remote_ref != "urn:li:share:1"

        with patch.object(
            type(lines), "_check_remote_post_exists", autospec=True, side_effect=check
        ):
            self.assertEqual(lines._check_remote_posts_exist(), lines[1])
        self.assertEqual(lines[0].state, "posted")

    def test_register_remote_posts_gone_marks_only_the_confirmed(self):
        """The bulk entry point writes on the confirmed lines and no others."""
        lines = self._create_suspect_lines(3)
        with patch.object(
            type(lines),
            "_check_remote_post_exists",
            autospec=True,
            side_effect=lambda line: line.remote_ref != "urn:li:share:1",
        ):
            self.assertEqual(lines._register_remote_posts_gone(), lines[1])
        self.assertEqual(lines[1].state, "deleted")
        self.assertFalse(lines[1].post_account_url)
        self.assertEqual(lines[1].remote_ref, "urn:li:share:1")
        for line in lines[0] | lines[2]:
            self.assertEqual(line.state, "posted")
            self.assertTrue(line.post_account_url)

    def test_register_remote_posts_gone_asks_nothing_about_nothing(self):
        """An empty batch of suspects reaches neither the social media nor the
        database."""
        with patch.object(
            type(self.SocialPostAccount), "_check_remote_post_exists", autospec=True
        ) as check:
            self.assertFalse(self.SocialPostAccount._register_remote_posts_gone())
        check.assert_not_called()
        self.assertNotEqual(self.social_post_account_id.state, "deleted")
