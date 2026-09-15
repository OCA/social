# Copyright 2026 Binhex <https://www.binhex.cloud>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from unittest.mock import patch

import psycopg2
from freezegun import freeze_time
from psycopg2 import errorcodes

from odoo import _, fields
from odoo.exceptions import UserError
from odoo.tests.common import tagged
from odoo.tools import mute_logger

from .test_social_sync_common import PATCH_SYNC_ACCOUNT, TestSocialMediaSyncCommon

LOGGER_ACCOUNT = "odoo.addons.social_media_sync.models.social_account"


@tagged("post_install", "-at_install")
class TestSocialAccountSync(TestSocialMediaSyncCommon):
    @staticmethod
    def _report_imported(accounts, post_id, domain, imported=None):
        """Stand for a connector that did read the accounts it was given."""
        if imported is not None:
            imported.update(accounts.ids)
        return []

    def test_action_full_resync(self):
        """The account form button delegates on the connector hook."""
        with patch(PATCH_SYNC_ACCOUNT.format("_full_resync"), autospec=True) as mock:
            self.social_account_id.action_full_resync()
            mock.assert_called_once()

    def test_action_full_resync_needs_a_single_account(self):
        other_account = self.SocialAccount.create(
            {"name": "Other account", "media_id": self.social_media_id.id}
        )
        with self.assertRaises(ValueError):
            (self.social_account_id | other_account).action_full_resync()

    def test_check_media_updates_leaves_out_a_pending_initial_sync(self):
        """The two crons run in parallel threads and write the same row.

        An account whose posts are being imported is answered for by that
        import, so checking it there only buys a serialization failure.
        """
        self.assertIn(
            ("pending_initial_sync", "=", False),
            self.SocialAccount._get_check_media_updates_domain(),
        )
        self.social_account_id.pending_initial_sync = True
        with patch.object(
            type(self.social_account_id),
            "validate_access_token",
            autospec=True,
        ) as mock_validate:
            self.SocialAccount._run_check_media_updates()
        self.assertNotIn(
            self.social_account_id.id,
            [call[0][0].id for call in mock_validate.call_args_list],
        )

    def test_nobody_adds_up_the_statistics_onto_the_account(self):
        """The connectors write rows; the figures of the account are derived.

        ``_filter_statistics`` summed the tuple of a connector straight onto
        the account, engagement included, which is not a figure a sum answers.
        Its last caller is gone and so is it.
        """
        self.assertFalse(
            hasattr(self.social_account_id, "_filter_statistics"),
            msg="Nothing may aggregate a connector tuple onto the account.",
        )

    def test_update_posts_statistics(self):
        fake_statistics = [{"like_count": 5}]
        with patch.object(
            type(self.social_account_id),
            "_update_posts_statistics",
            autospec=True,
            return_value=fake_statistics,
        ):
            update_statistics = self.social_account_id.update_posts_statistics()
            self.assertEqual(update_statistics[0]["like_count"], 5)

    def test_update_posts_statistics_clears_the_pending_initial_sync(self):
        """The manual update is the very import the cron was going to run.

        The dashboard announces a background import while the flag is set, so
        the button that does the import itself is what takes it down.
        """
        self.social_account_id.pending_initial_sync = True
        with patch.object(
            type(self.social_account_id),
            "_update_posts_statistics",
            autospec=True,
            side_effect=self._report_imported,
        ):
            self.social_account_id.update_posts_statistics()
        self.assertFalse(self.social_account_id.pending_initial_sync)

    def test_update_posts_statistics_keeps_the_flag_of_a_skipped_import(self):
        """An import the connector did not run is not an import.

        A connector answers the same figures whether it read the social media
        or the quota stopped it, so what tells the two apart is what it
        reports as read. An account nobody read still needs its first import,
        and clearing the flag would take it out of the monthly cron for good.
        """
        self.social_account_id.pending_initial_sync = True
        with patch.object(
            type(self.social_account_id),
            "_update_posts_statistics",
            autospec=True,
            return_value=[],
        ):
            self.social_account_id.update_posts_statistics()
        self.assertTrue(self.social_account_id.pending_initial_sync)

    def test_full_resync_falls_back_to_the_ordinary_refresh(self):
        """A media with no notion of a whole feed has nothing extra to do."""
        with patch.object(
            type(self.social_account_id),
            "update_posts_statistics",
            autospec=True,
            return_value="[]",
        ) as patch_update:
            self.social_account_id._full_resync()
        patch_update.assert_called_once()

    def test_full_resync_on_no_accounts_does_nothing(self):
        """No accounts is not every account.

        A connector delegates here the accounts it does not handle, and the
        ordinary refresh takes an empty recordset as every account: falling
        back on it would refresh a second time the very accounts the
        connector already reconciled.
        """
        with patch.object(
            type(self.social_account_id),
            "update_posts_statistics",
            autospec=True,
            return_value="[]",
        ) as patch_update:
            self.SocialAccount.browse()._full_resync()
        patch_update.assert_not_called()

    def test_run_full_resync_leaves_out_a_pending_initial_sync(self):
        """The initial sync is this very pass: the two must not fight."""
        self.social_account_id.pending_initial_sync = True
        with patch.object(
            type(self.social_account_id), "_full_resync", autospec=True
        ) as patch_resync:
            self.SocialAccount._run_full_resync()
        self.assertNotIn(
            self.social_account_id,
            [call[0][0] for call in patch_resync.call_args_list],
        )

    @mute_logger("odoo.addons.social_media_sync.models.social_account")
    def test_run_full_resync_isolates_each_account(self):
        """The account that fails must not stop the ones still to come."""
        failing = self.social_account_id
        working = failing.copy({"name": "Other", "username": "other-account"})

        def resync(account):
            if account.id == failing.id:
                raise UserError(_("The social media refused the feed"))

        with patch.object(
            type(failing), "_full_resync", autospec=True, side_effect=resync
        ) as patch_resync:
            self.SocialAccount._run_full_resync()
        resynced = [call[0][0] for call in patch_resync.call_args_list]
        self.assertIn(working, resynced)

    @mute_logger("odoo.addons.social_media_sync.models.social_account")
    def test_run_full_resync_reraises_a_concurrency_error(self):
        """A cron gets no retry of its own, so Odoo has to keep seeing it."""

        class ConcurrencyError(psycopg2.OperationalError):
            pgcode = errorcodes.SERIALIZATION_FAILURE

        with patch.object(
            type(self.social_account_id),
            "_full_resync",
            autospec=True,
            side_effect=ConcurrencyError("serialization conflict"),
        ):
            with self.assertRaises(psycopg2.OperationalError):
                self.SocialAccount._run_full_resync()

    def test_full_resync_cron_runs_weekly(self):
        """Reading every publication is the expensive pass, so it runs seldom."""
        cron = self.env.ref("social_media_sync.full_resync_account_job")
        self.assertTrue(cron.active)
        self.assertEqual(cron.interval_number, 1)
        self.assertEqual(cron.interval_type, "weeks")
        self.assertEqual(cron.code, "model._run_full_resync()")

    def test_trigger_initial_sync(self):
        CronTrigger = self.env["ir.cron.trigger"]
        cron = self.env.ref("social_media_sync.initial_sync_account_job")
        before = CronTrigger.search_count([("cron_id", "=", cron.id)])
        self.social_account_id._trigger_initial_sync()
        after = CronTrigger.search_count([("cron_id", "=", cron.id)])
        self.assertEqual(after, before + 1)
        self.assertTrue(self.social_account_id.pending_initial_sync)

    def test_trigger_initial_sync_waits_for_the_association_to_commit(self):
        CronTrigger = self.env["ir.cron.trigger"]
        cron = self.env.ref("social_media_sync.initial_sync_account_job")
        before = CronTrigger.search([("cron_id", "=", cron.id)])
        with freeze_time("2025-01-01 10:00:00"):
            self.social_account_id._trigger_initial_sync()
        trigger = CronTrigger.search([("cron_id", "=", cron.id)]) - before
        self.assertEqual(len(trigger), 1)
        self.assertEqual(
            trigger.call_at,
            fields.Datetime.to_datetime("2025-01-01 10:00:15"),
            "The import starts once the association that asked for it has "
            "committed the account it writes on",
        )

    def test_trigger_initial_sync_without_accounts(self):
        CronTrigger = self.env["ir.cron.trigger"]
        cron = self.env.ref("social_media_sync.initial_sync_account_job")
        before = CronTrigger.search_count([("cron_id", "=", cron.id)])
        self.SocialAccount._trigger_initial_sync()
        after = CronTrigger.search_count([("cron_id", "=", cron.id)])
        self.assertEqual(after, before)

    def test_run_initial_sync(self):
        self.social_account_id.pending_initial_sync = True
        with patch(
            PATCH_SYNC_ACCOUNT.format("_update_posts_statistics"),
            autospec=True,
            side_effect=self._report_imported,
        ) as patch_update, patch(
            PATCH_SYNC_ACCOUNT.format("_notify_posts_updated"), autospec=True
        ) as patch_notify:
            self.SocialAccount._run_initial_sync()
        patch_update.assert_called_once()
        patch_notify.assert_called_once()
        self.assertFalse(self.social_account_id.pending_initial_sync)

    def test_run_initial_sync_retries_an_account_the_connector_skipped(self):
        """A skipped import is not a failure, so it is not recorded as one.

        Nothing went wrong: the social media was not read, and the quota
        notice already went to the user. What the account cannot do is keep
        the flag with nobody coming back for it, because the flag is also what
        keeps the bihourly check away from it.
        """
        self.social_account_id.pending_initial_sync = True
        before = len(self.social_account_id.message_ids)
        with patch(
            PATCH_SYNC_ACCOUNT.format("_update_posts_statistics"),
            autospec=True,
            return_value=[],
        ), patch(
            PATCH_SYNC_ACCOUNT.format("_notify_posts_updated"), autospec=True
        ), patch(
            PATCH_SYNC_ACCOUNT.format("_reschedule_initial_sync"), autospec=True
        ) as patch_reschedule:
            self.SocialAccount._run_initial_sync()
        self.assertTrue(self.social_account_id.pending_initial_sync)
        self.assertEqual(
            patch_reschedule.call_args[0][0],
            self.social_account_id,
            "The account nobody read is the one to import again",
        )
        self.assertEqual(
            len(self.social_account_id.message_ids),
            before,
            "A skipped import is not a failure to record on the account",
        )

    @mute_logger(LOGGER_ACCOUNT)
    def test_run_initial_sync_clears_the_flag_on_error(self):
        """The dashboard waits on the flag, and nobody retries the sync.

        The cron only runs once a month, so keeping the flag after a failure
        would leave the view waiting forever. The reason is left on the
        account instead, because the cron has no user connected to receive the
        notification of the connectors.
        """
        self.social_account_id.pending_initial_sync = True
        before = len(self.social_account_id.message_ids)
        with patch(
            PATCH_SYNC_ACCOUNT.format("update_posts_statistics"),
            autospec=True,
            side_effect=ValueError("boom"),
        ), patch(
            PATCH_SYNC_ACCOUNT.format("_notify_posts_updated"), autospec=True
        ) as patch_notify:
            self.SocialAccount._run_initial_sync()
        patch_notify.assert_called_once()
        self.assertFalse(self.social_account_id.pending_initial_sync)
        messages = self.social_account_id.message_ids
        self.assertEqual(len(messages) - before, 1)
        self.assertIn("boom", messages[0].body)
        self.assertIn(
            self.social_account_id.user_id.partner_id,
            messages[0].partner_ids,
        )

    def test_run_initial_sync_retries_an_account_that_lost_a_race(self):
        """A concurrency error is retried, not recorded as a failure.

        The write that lost the race is the whole import, and the cron only
        runs once a month: clearing the flag would tell the dashboard about
        posts that were never brought in, and the retry Odoo does on a
        concurrency error covers the web requests, not the crons.
        """

        class ConcurrencyError(psycopg2.OperationalError):
            pgcode = errorcodes.SERIALIZATION_FAILURE

        self.social_account_id.pending_initial_sync = True
        with patch(
            PATCH_SYNC_ACCOUNT.format("update_posts_statistics"),
            autospec=True,
            side_effect=ConcurrencyError("serialization conflict"),
        ), patch(
            PATCH_SYNC_ACCOUNT.format("_close_initial_sync"), autospec=True
        ) as patch_close, patch(
            PATCH_SYNC_ACCOUNT.format("_reschedule_initial_sync"), autospec=True
        ) as patch_reschedule:
            self.SocialAccount._run_initial_sync()
        patch_close.assert_not_called()
        patch_reschedule.assert_called_once()
        self.assertEqual(
            patch_reschedule.call_args[0][0],
            self.social_account_id,
            "The account that lost the race is the one to import again",
        )

    def test_run_initial_sync_does_not_reschedule_what_it_imported(self):
        self.social_account_id.pending_initial_sync = True
        with patch(
            PATCH_SYNC_ACCOUNT.format("_update_posts_statistics"),
            autospec=True,
            side_effect=self._report_imported,
        ), patch(
            PATCH_SYNC_ACCOUNT.format("_notify_posts_updated"), autospec=True
        ), patch(
            PATCH_SYNC_ACCOUNT.format("_reschedule_initial_sync"), autospec=True
        ) as patch_reschedule:
            self.SocialAccount._run_initial_sync()
        self.assertFalse(patch_reschedule.call_args[0][0])

    def test_reschedule_initial_sync_asks_the_cron_for_a_later_run(self):
        CronTrigger = self.env["ir.cron.trigger"]
        cron = self.env.ref("social_media_sync.initial_sync_account_job")
        before = CronTrigger.search([("cron_id", "=", cron.id)])
        with freeze_time("2025-01-01 10:00:00"):
            self.social_account_id._reschedule_initial_sync()
        trigger = CronTrigger.search([("cron_id", "=", cron.id)]) - before
        self.assertEqual(len(trigger), 1)
        self.assertEqual(
            trigger.call_at,
            fields.Datetime.to_datetime("2025-01-01 10:05:00"),
            "An account is retried once the update that took it is over",
        )

    def test_reschedule_initial_sync_without_accounts(self):
        CronTrigger = self.env["ir.cron.trigger"]
        cron = self.env.ref("social_media_sync.initial_sync_account_job")
        before = CronTrigger.search_count([("cron_id", "=", cron.id)])
        self.SocialAccount._reschedule_initial_sync()
        after = CronTrigger.search_count([("cron_id", "=", cron.id)])
        self.assertEqual(after, before)

    def test_notify_posts_updated(self):
        """What the dashboard listens for: the type, the account and the text.

        The whole payload is asserted, not only the account: the notice
        travels on a type of its own while it is worded as an information
        message, and the card reads both.
        """
        account = self.social_account_id
        Bus = self.env["bus.bus"]
        with patch.object(type(Bus), "_sendone", autospec=True) as patch_sendone:
            account._notify_posts_updated()
        patch_sendone.assert_called_once()
        self.assertEqual(patch_sendone.call_args[0][1], account.user_id.partner_id)
        self.assertEqual(patch_sendone.call_args[0][2], "social_posts_updated")
        self.assertEqual(
            patch_sendone.call_args[0][3],
            {
                "account_id": account.id,
                "message_type": "info",
                "message": account._format_user_notification(
                    "The posts of the account were updated.",
                    media=account.media_type or account.media_id.name,
                    account_name=account.name,
                    message_type="info",
                ),
            },
        )
        self.assertIn(
            account.name,
            patch_sendone.call_args[0][3]["message"],
            "A user may be responsible for several accounts, so the message "
            "has to name the one that was updated",
        )

    def test_flag_posts_need_import_announces_it_once(self):
        """The notice goes up, and a second pass does not push it again.

        The check runs every two hours over an account only the import can
        clear, so announcing it again would push the same message at the user
        for something the dashboard is already drawing.
        """
        Bus = self.env["bus.bus"]
        with patch.object(type(Bus), "_sendone", autospec=True) as patch_sendone:
            self.social_account_id._flag_posts_need_import()
            self.social_account_id._flag_posts_need_import()
        self.assertTrue(self.social_account_id.posts_need_import)
        patch_sendone.assert_called_once()
        self.assertEqual(patch_sendone.call_args[0][2], "social_posts_need_import")
        self.assertTrue(patch_sendone.call_args[0][3]["need_update"])

    def test_clear_posts_need_import_takes_the_notice_down(self):
        """The import that brings the publications in is what resolves it."""
        self.social_account_id.posts_need_import = True
        Bus = self.env["bus.bus"]
        with patch.object(type(Bus), "_sendone", autospec=True) as patch_sendone:
            self.social_account_id._clear_posts_need_import()
        self.assertFalse(self.social_account_id.posts_need_import)
        self.assertEqual(patch_sendone.call_args[0][2], "social_posts_need_import")
        self.assertFalse(patch_sendone.call_args[0][3]["need_update"])

    def test_clear_posts_need_import_says_nothing_when_it_was_down(self):
        """An account announcing nothing has no notice to take down."""
        self.social_account_id.posts_need_import = False
        Bus = self.env["bus.bus"]
        with patch.object(type(Bus), "_sendone", autospec=True) as patch_sendone:
            self.social_account_id._clear_posts_need_import()
        patch_sendone.assert_not_called()

    def test_notify_posts_need_import_names_the_accounts(self):
        """The dashboard has to say which account to import."""
        Bus = self.env["bus.bus"]
        with patch.object(type(Bus), "_sendone", autospec=True) as patch_sendone:
            self.social_account_id._notify_posts_need_import()
        self.assertEqual(
            patch_sendone.call_args[0][3]["accounts"],
            [
                {
                    "id": self.social_account_id.id,
                    "name": self.social_account_id.name,
                    "media": self.social_account_id.media_id.name,
                }
            ],
        )

    def test_notify_posts_need_import_tells_each_user_of_his_own(self):
        """Each responsible hears about his accounts and about no others."""
        other_user = self.env["res.users"].create(
            {"name": "Other responsible", "login": "other-responsible"}
        )
        other_account = self.SocialAccount.create(
            {
                "name": "Other account",
                "media_id": self.social_media_id.id,
                "user_id": other_user.id,
            }
        )
        Bus = self.env["bus.bus"]
        with patch.object(type(Bus), "_sendone", autospec=True) as patch_sendone:
            (self.social_account_id | other_account)._notify_posts_need_import()
        self.assertEqual(patch_sendone.call_count, 2)
        named = {
            call[0][1]: [account["id"] for account in call[0][3]["accounts"]]
            for call in patch_sendone.call_args_list
        }
        self.assertEqual(
            named[self.social_account_id.user_id.partner_id],
            [self.social_account_id.id],
        )
        self.assertEqual(named[other_user.partner_id], [other_account.id])

    def test_update_posts_statistics_clears_posts_need_import(self):
        """The import the notice asked for is what takes it down."""
        self.social_account_id.posts_need_import = True
        with patch.object(
            type(self.social_account_id),
            "_update_posts_statistics",
            autospec=True,
            side_effect=self._report_imported,
        ):
            self.social_account_id.update_posts_statistics()
        self.assertFalse(self.social_account_id.posts_need_import)

    def test_update_posts_statistics_keeps_the_notice_of_a_skipped_import(self):
        """An import the quota stopped brought nothing in to announce."""
        self.social_account_id.posts_need_import = True
        with patch.object(
            type(self.social_account_id),
            "_update_posts_statistics",
            autospec=True,
            return_value=[],
        ):
            self.social_account_id.update_posts_statistics()
        self.assertTrue(self.social_account_id.posts_need_import)

    def test_detects_pending_posts_is_off_by_default(self):
        """A social media that cannot tell says so, and is imported anyway."""
        self.assertFalse(self.social_account_id._detects_pending_posts())

    def test_accounts_to_import_keeps_a_media_that_cannot_detect(self):
        """Its only source is the timeline, and reading it is the import.

        Without this rule the filter would leave those accounts out for good:
        they can never carry a flag their connector cannot raise.
        """
        self.social_account_id.write(
            {"posts_need_import": False, "pending_initial_sync": False}
        )
        self.assertEqual(
            self.social_account_id._accounts_to_import(), self.social_account_id
        )

    def test_accounts_to_import_narrows_a_media_that_can_detect(self):
        """A connector that knows what moved spends nothing on what did not."""
        quiet = self.SocialAccount.create(
            {"name": "Quiet account", "media_id": self.social_media_id.id}
        )
        self.social_account_id.posts_need_import = True
        with patch.object(
            type(self.SocialAccount),
            "_detects_pending_posts",
            autospec=True,
            return_value=True,
        ):
            self.assertEqual(
                (self.social_account_id | quiet)._accounts_to_import(),
                self.social_account_id,
            )

    def test_accounts_to_import_keeps_a_pending_initial_sync(self):
        """The button is what unblocks a first import that failed.

        A freshly associated account has been through no check, so nothing
        could have flagged it.
        """
        self.social_account_id.write(
            {"posts_need_import": False, "pending_initial_sync": True}
        )
        with patch.object(
            type(self.SocialAccount),
            "_detects_pending_posts",
            autospec=True,
            return_value=True,
        ):
            self.assertEqual(
                self.social_account_id._accounts_to_import(), self.social_account_id
            )

    def test_update_posts_statistics_narrows_what_it_reads(self):
        """Asked for every account, only the ones behind cost a call."""
        quiet = self.SocialAccount.create(
            {"name": "Quiet account", "media_id": self.social_media_id.id}
        )
        self.social_account_id.posts_need_import = True
        with patch.object(
            type(self.SocialAccount),
            "_detects_pending_posts",
            autospec=True,
            return_value=True,
        ), patch.object(
            type(self.SocialAccount),
            "_update_posts_statistics",
            autospec=True,
            side_effect=self._report_imported,
        ) as mock_update:
            self.SocialAccount.update_posts_statistics()
        self.assertEqual(mock_update.call_args[0][0], self.social_account_id)
        self.assertNotIn(quiet, mock_update.call_args[0][0])

    def test_update_posts_statistics_reads_the_account_it_was_given(self):
        """*Update* on one card imports it, flagged or not.

        The user already said which account he wants; the narrowing is only
        there to save the calls nobody asked for.
        """
        self.social_account_id.write(
            {"posts_need_import": False, "pending_initial_sync": False}
        )
        with patch.object(
            type(self.SocialAccount),
            "_detects_pending_posts",
            autospec=True,
            return_value=True,
        ), patch.object(
            type(self.SocialAccount),
            "_update_posts_statistics",
            autospec=True,
            side_effect=self._report_imported,
        ) as mock_update:
            self.social_account_id.update_posts_statistics()
        self.assertEqual(mock_update.call_args[0][0], self.social_account_id)

    def test_update_posts_statistics_hands_no_account_when_none_moved(self):
        """An empty recordset is every account to the connectors.

        So a narrowing that keeps nothing has to stop instead of handing them
        one, and the empty answer is what the dashboard words the button from.
        """
        self.social_account_id.write(
            {"posts_need_import": False, "pending_initial_sync": False}
        )
        with patch.object(
            type(self.SocialAccount),
            "_detects_pending_posts",
            autospec=True,
            return_value=True,
        ), patch.object(
            type(self.SocialAccount),
            "_update_posts_statistics",
            autospec=True,
        ) as mock_update:
            answer = self.SocialAccount.update_posts_statistics()
        mock_update.assert_not_called()
        self.assertEqual(answer, [])
