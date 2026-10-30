# Copyright 2026 Binhex <https://www.binhex.cloud>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from datetime import timedelta
from unittest.mock import patch

from odoo import fields
from odoo.tools import mute_logger

from odoo.addons.social_media_base.models.social_account import (
    STATISTICS_WINDOW_DAYS,
)

from .test_social_common import PATCH_ACCOUNT, TestSocialMediaBaseCommon

LOG_PATH = "odoo.addons.social_media_base.models.social_account"


class TestSocialPostStatisticsBase(TestSocialMediaBaseCommon):
    """Reading the figures of a publication back from the social media."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.now = fields.Datetime.now()
        cls.other_account_id = cls.SocialAccount.create(
            {
                "name": "Linkedin Second",
                "media_id": cls.social_media_id.id,
            }
        )

    def _publication(self, account=None, days_ago=1, **values):
        """Create a publication that is online and inside the window."""
        return self.SocialPostAccount.create(
            dict(
                {
                    "post_id": self.social_post_id.id,
                    "account_id": (account or self.social_account_id).id,
                    "message": "Test message",
                    "state": "posted",
                    "remote_ref": "remote-ref",
                    "published_date": self.now - timedelta(days=days_ago),
                },
                **values,
            )
        )

    def _window_lines(self, account):
        return self.SocialPostAccount.search(account._statistics_window_domain())

    def test_statistics_date_starts_empty(self):
        """A publication nobody read carries no date.

        It is what tells a zero nobody asked about apart from a zero the
        social media really reported.
        """
        self.assertFalse(self.social_post_account_id.statistics_date)

    def test_statistics_date_is_readonly(self):
        """Only the refresh writes the date, never the user."""
        field = self.SocialPostAccount._fields["statistics_date"]
        self.assertTrue(field.readonly)
        self.assertFalse(field.copy)

    def test_statistics_window_is_a_month(self):
        """The window is a constant of the module, not a setting.

        It is the cost decision that lets this pass live in
        ``social_media_base``, so it is not a preference to widen.
        """
        self.assertEqual(STATISTICS_WINDOW_DAYS, 30)

    def test_window_keeps_the_recent_publication(self):
        """A publication of the day before the limit is still asked about."""
        recent = self._publication(days_ago=STATISTICS_WINDOW_DAYS - 1)
        self.assertIn(recent, self._window_lines(self.social_account_id))

    def test_window_leaves_out_the_old_publication(self):
        """One day past the limit is one day out of the pass, for good.

        Nothing widens the window afterwards, which is what gives the pass a
        fixed cost.
        """
        old = self._publication(days_ago=STATISTICS_WINDOW_DAYS + 1)
        self.assertNotIn(old, self._window_lines(self.social_account_id))

    def test_window_leaves_out_the_deleted_publication(self):
        """A publication gone from the social media has nothing left to ask."""
        deleted = self._publication(state="deleted")
        self.assertNotIn(deleted, self._window_lines(self.social_account_id))

    def test_window_leaves_out_the_publication_without_reference(self):
        """Without a ``remote_ref`` there is nothing to ask the figures of."""
        unknown = self._publication(remote_ref=False)
        self.assertNotIn(unknown, self._window_lines(self.social_account_id))

    def test_window_leaves_out_another_account(self):
        """Every account is asked about its own publications only."""
        other = self._publication(account=self.other_account_id)
        self.assertNotIn(other, self._window_lines(self.social_account_id))

    def test_the_pass_hands_the_window_to_the_connector(self):
        """The connector receives exactly the lines of the window.

        The pass chooses, the hook spends: what the connector is handed is
        what base decided is worth a call.
        """
        inside = self._publication(days_ago=1)
        outside = self._publication(days_ago=STATISTICS_WINDOW_DAYS + 1)
        with patch(
            PATCH_ACCOUNT.format("_refresh_post_statistics"),
            autospec=True,
            side_effect=lambda account, lines: lines,
        ) as hook:
            refreshed = self.social_account_id._refresh_window_statistics()
        handed = hook.call_args.args[1]
        self.assertIn(inside, handed)
        self.assertNotIn(outside, handed)
        self.assertEqual(refreshed, handed)

    def test_the_pass_spends_nothing_without_a_connector(self):
        """The empty hook answers no line, so nothing is stamped.

        With no connector installed the pass walks the accounts and asks
        nobody: it is the connector that spends the call.
        """
        publication = self._publication()
        self.assertFalse(self.social_account_id._refresh_window_statistics())
        self.assertFalse(publication.statistics_date)

    def test_an_account_without_publications_is_not_asked_about(self):
        """No line in the window, no call for that account."""
        self._publication(account=self.social_account_id)
        accounts = self.social_account_id + self.other_account_id
        with patch(
            PATCH_ACCOUNT.format("_refresh_post_statistics"),
            autospec=True,
            side_effect=lambda account, lines: lines,
        ) as hook:
            accounts._refresh_window_statistics()
        self.assertEqual(hook.call_count, 1)

    def test_the_cron_runs_once_a_day(self):
        """Daily and active out of the box.

        The figures move slowly and the quotas are counted per day, and a
        deactivated cron would leave the feature looking broken on a fresh
        install, which is what it exists to fix.
        """
        cron = self.env.ref("social_media_base.refresh_post_statistics_job")
        self.assertEqual(cron.interval_number, 1)
        self.assertEqual(cron.interval_type, "days")
        self.assertEqual(cron.numbercall, -1)
        self.assertTrue(cron.active)
        self.assertEqual(cron.model_id.model, "social.account")

    def test_the_cron_reads_the_window(self):
        """The daily pass asks about the publications inside the window."""
        inside = self._publication(days_ago=1)
        outside = self._publication(days_ago=STATISTICS_WINDOW_DAYS + 1)
        with patch(
            PATCH_ACCOUNT.format("_refresh_post_statistics"),
            autospec=True,
            side_effect=lambda account, lines: lines,
        ) as hook:
            self.SocialAccount._run_refresh_post_statistics()
        handed = self.SocialPostAccount.union(
            *[call.args[1] for call in hook.call_args_list]
        )
        self.assertIn(inside, handed)
        self.assertNotIn(outside, handed)

    def test_the_cron_leaves_out_the_expired_credentials(self):
        """An account waiting for a new authorization spends no call.

        It could only answer a refusal, so asking it would spend a call to
        learn what the flag already says.
        """
        self._publication(account=self.other_account_id)
        self.other_account_id.need_update = True
        with patch(
            PATCH_ACCOUNT.format("_refresh_post_statistics"),
            autospec=True,
            side_effect=lambda account, lines: lines,
        ) as hook:
            self.SocialAccount._run_refresh_post_statistics()
        asked = [call.args[0] for call in hook.call_args_list]
        self.assertNotIn(self.other_account_id, asked)

    def test_the_button_reads_the_same_set_as_the_cron(self):
        """*Update* on the dashboard asks for the window and nothing else.

        A single set to explain and a single ceiling of cost, wherever the
        user presses.
        """
        inside = self._publication(days_ago=1)
        outside = self._publication(days_ago=STATISTICS_WINDOW_DAYS + 1)
        with patch(
            PATCH_ACCOUNT.format("_refresh_post_statistics"),
            autospec=True,
            side_effect=lambda account, lines: lines,
        ) as hook:
            self.social_account_id.refresh_dashboard_statistics()
        handed = hook.call_args.args[1]
        self.assertIn(inside, handed)
        self.assertNotIn(outside, handed)

    def test_the_account_form_button_reads_the_window_too(self):
        """*Refresh statistics* of the form reads the same window."""
        publication = self._publication(days_ago=1)
        with patch(
            PATCH_ACCOUNT.format("_refresh_post_statistics"),
            autospec=True,
            side_effect=lambda account, lines: lines,
        ) as hook:
            self.social_account_id.action_refresh_statistics()
        self.assertIn(publication, hook.call_args.args[1])

    @mute_logger(LOG_PATH)
    def test_an_account_that_fails_does_not_stop_the_next(self):
        """Each account is read inside its own savepoint.

        The pass writes as it goes, so the social media refusing one account
        must not undo what another one already wrote nor keep it from being
        asked at all.
        """
        broken = self._publication(account=self.social_account_id)
        working = self._publication(account=self.other_account_id)
        read = self.SocialPostAccount

        def refresh(account, lines):
            if account == self.social_account_id:
                raise ValueError("The social media refused this account")
            lines.write({"statistics_date": self.now})
            return lines

        with patch(
            PATCH_ACCOUNT.format("_refresh_post_statistics"),
            autospec=True,
            side_effect=refresh,
        ):
            accounts = self.social_account_id + self.other_account_id
            read = accounts._refresh_window_statistics()
        self.assertEqual(read, working)
        self.assertFalse(broken.statistics_date)
        self.assertTrue(working.statistics_date)
