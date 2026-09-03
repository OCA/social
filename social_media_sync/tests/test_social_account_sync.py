# Copyright 2026 Binhex <https://www.binhex.cloud>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import json
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

    def test_backfill_statistics_does_nothing_without_a_connector(self):
        """Reading the history backwards is the connector's, like the rest."""
        self.assertIsNone(self.social_account_id._backfill_statistics())

    def test_filter_statistics(self):
        fake_statistics = {"stats_fake": (5, 10, 15, 20, 25, 30)}
        statistics = self.social_account_id._filter_statistics(fake_statistics)
        self.assertEqual(statistics["click_count"], fake_statistics["stats_fake"][0])
        self.assertEqual(statistics["like_count"], fake_statistics["stats_fake"][1])
        self.assertEqual(statistics["comment_count"], fake_statistics["stats_fake"][2])
        self.assertEqual(statistics["share_count"], fake_statistics["stats_fake"][3])
        self.assertEqual(statistics["engagement"], fake_statistics["stats_fake"][4])
        self.assertEqual(
            statistics["impression_count"], fake_statistics["stats_fake"][5]
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
            load_update_statistics = json.loads(update_statistics)
            self.assertEqual(load_update_statistics[0]["like_count"], 5)

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
            return_value=[],
        ):
            self.social_account_id.update_posts_statistics()
        self.assertFalse(self.social_account_id.pending_initial_sync)

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
            PATCH_SYNC_ACCOUNT.format("update_posts_statistics"), autospec=True
        ) as patch_update, patch(
            PATCH_SYNC_ACCOUNT.format("_notify_posts_updated"), autospec=True
        ) as patch_notify:
            self.SocialAccount._run_initial_sync()
        patch_update.assert_called_once()
        patch_notify.assert_called_once()
        self.assertFalse(self.social_account_id.pending_initial_sync)

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
            PATCH_SYNC_ACCOUNT.format("update_posts_statistics"), autospec=True
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
        Bus = self.env["bus.bus"]
        with patch.object(type(Bus), "_sendone", autospec=True) as patch_sendone:
            self.social_account_id._notify_posts_updated()
        patch_sendone.assert_called_once()
        self.assertEqual(
            patch_sendone.call_args[0][1], self.social_account_id.user_id.partner_id
        )
        self.assertEqual(patch_sendone.call_args[0][2], "social_posts_updated")
        payload = patch_sendone.call_args[0][3]
        self.assertEqual(payload["account_id"], self.social_account_id.id)
        self.assertIn(
            self.social_account_id.name,
            payload["message"],
            "A user may be responsible for several accounts, so the message "
            "has to name the one that was updated",
        )
