# Copyright 2026 Binhex <https://www.binhex.cloud>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from datetime import timedelta
from unittest.mock import patch

import psycopg2
from psycopg2 import errorcodes

from odoo import _, fields
from odoo.exceptions import UserError
from odoo.tools import mute_logger

from odoo.addons.social_media_linkedin.social_linkedin_utils import (
    _UPDATE_CHECK_DAYS_LINKEDIN,
    epoch_milliseconds,
)
from odoo.addons.social_media_linkedin.tests.test_common_linkedin import (
    PATCH_ACCOUNT_LINKEDIN,
    RECENT_STATISTICS_LINKEDIN,
    _linkedin_buckets,
    _linkedin_day,
)
from odoo.addons.social_media_sync.tests.test_social_sync_common import (
    PATCH_SYNC_ACCOUNT,
)

from .test_sync_linkedin_common import (
    PATCH_SYNC_ACCOUNT_LINKEDIN,
    TestSocialSyncCommonLinkedin,
)

LOGGER_ACCOUNT_LINKEDIN = "odoo.addons.social_media_linkedin.models.social_account"
LOGGER_ACCOUNT_SYNC_LINKEDIN = (
    "odoo.addons.social_media_linkedin_sync.models.social_account"
)


class TestSocialSyncCheckLinkedin(TestSocialSyncCommonLinkedin):
    """The bihourly check: what moved on the page since the last import."""

    def _mark_the_page_as_imported(self, accounts=None, statistics=None):
        """Leave on the accounts the mark a previous import would have left."""
        accounts = accounts or self.SocialAccountLinkedin
        accounts.linkedin_statistics_checkpoint = (
            accounts._linkedin_statistics_checkpoint(
                statistics or RECENT_STATISTICS_LINKEDIN
            )
        )

    def test_linkedin_check_days_is_the_window_of_the_check(self):
        """The days compared are the last ones, today included."""
        today = fields.Date.today()
        days = self.SocialAccountLinkedin._linkedin_check_days()
        self.assertEqual(len(days), _UPDATE_CHECK_DAYS_LINKEDIN)
        self.assertEqual(
            max(days),
            today.isoformat(),
            msg="The bucket of today is the one the check is really after.",
        )
        self.assertEqual(
            min(days),
            (today - timedelta(days=_UPDATE_CHECK_DAYS_LINKEDIN - 1)).isoformat(),
        )

    def test_linkedin_watched_figures_trims_the_day_and_the_engagement(self):
        """The sweep reads one day more than the check compares."""
        buckets = _linkedin_buckets(RECENT_STATISTICS_LINKEDIN)
        eighth_day = (
            fields.Date.today() - timedelta(days=_UPDATE_CHECK_DAYS_LINKEDIN)
        ).isoformat()
        buckets[eighth_day] = (9, 9, 9, 9, 0.9, 99)
        self.assertEqual(
            self.SocialAccountLinkedin._linkedin_watched_figures(buckets),
            RECENT_STATISTICS_LINKEDIN,
            msg="The extra day is dropped, and the engagement with it: it is "
            "a ratio of the others, so it moves on its own.",
        )

    def test_linkedin_watched_figures_without_figures(self):
        self.assertEqual(self.SocialAccountLinkedin._linkedin_watched_figures({}), {})

    def test_linkedin_read_watched_figures_asks_the_window_of_the_sweep(self):
        """The import leaves the mark the sweep of a pass would have left."""
        buckets = _linkedin_buckets(RECENT_STATISTICS_LINKEDIN)
        with self._patch_reader(buckets) as mock_reader:
            statistics = self.SocialAccountLinkedin._linkedin_read_watched_figures()
        self.assertEqual(statistics, RECENT_STATISTICS_LINKEDIN)
        start_time, end_time, granularity = mock_reader.call_args.args[1:]
        self.assertEqual(granularity, "DAY")
        self.assertEqual(
            round((end_time - start_time) / (24 * 3600 * 1000)),
            _UPDATE_CHECK_DAYS_LINKEDIN + 1,
            msg="Asked over the window the sweep reads, then trimmed.",
        )
        self.assertGreater(
            end_time,
            epoch_milliseconds(fields.Datetime.now()),
            msg="LinkedIn takes the end of the interval as exclusive and "
            "normalizes it to the day, so a range ending now would leave the "
            "bucket of today out, the one bucket the check is after.",
        )

    def test_linkedin_statistics_snapshot_drops_what_is_not_a_checkpoint(self):
        """Only a mapping of days to lists of numbers reads as a baseline.

        The value comes from a stored column, so everything else has to read
        as "no baseline yet" and reseed instead of comparing wrongly.
        """
        account = self.SocialAccountLinkedin
        for label, stored in (
            ("empty", False),
            ("a bare string", "{not json"),
            ("a list", [1, 2]),
            ("a day", "2025-01-01"),
            ("a number", 17),
        ):
            with self.subTest(case=label):
                self.assertEqual(account._linkedin_statistics_snapshot(stored), {})
        # A dict is read, but a day whose figures are not a list of numbers
        # is dropped on its own: the rest of the mark is still usable.
        self.assertEqual(
            account._linkedin_statistics_snapshot(
                {
                    "2025-01-01": [1, 2.5],
                    "2025-01-02": 12,
                    "2025-01-03": "12",
                    "2025-01-04": ["12"],
                    "2025-01-05": {"clicks": 1},
                    "2025-01-06": None,
                }
            ),
            {"2025-01-01": [1, 2.5]},
        )

    def test_run_check_media_updates_takes_the_first_reading_as_the_mark(self):
        """An account with no mark yet gets one, and announces nothing."""
        self._isolate_linkedin_account()
        self.SocialAccountLinkedin.linkedin_statistics_checkpoint = False
        with self._patch_recent_statistics(), patch(
            PATCH_ACCOUNT_LINKEDIN.format("_get_posts"), autospec=True
        ) as mock_get_posts:
            self.assertFalse(self.SocialAccount._run_check_media_updates())
        self.assertEqual(
            self.SocialAccountLinkedin.linkedin_statistics_checkpoint,
            self.SocialAccountLinkedin._linkedin_statistics_checkpoint(
                RECENT_STATISTICS_LINKEDIN
            ),
        )
        self.assertFalse(self.SocialAccountLinkedin.posts_need_import)
        mock_get_posts.assert_not_called()

    def test_run_check_media_updates_reads_a_mark_written_before_the_move(self):
        """A checkpoint already stored keeps reading as a baseline.

        A value in the shape the column holds has to compare and not reseed,
        which would flag every active account on the first pass after
        deploying.
        """
        self._isolate_linkedin_account()
        # Built by hand, in the very form the column holds: the days keyed by
        # their ISO string, each one carrying its figures as a list of
        # numbers.
        stored = {
            day: list(figures)
            for day, figures in sorted(RECENT_STATISTICS_LINKEDIN.items())
        }
        self.assertEqual(
            stored,
            self.SocialAccountLinkedin._linkedin_statistics_checkpoint(
                RECENT_STATISTICS_LINKEDIN
            ),
            msg="The move changed the stored form of a checkpoint.",
        )
        self.SocialAccountLinkedin.linkedin_statistics_checkpoint = stored
        with self._patch_recent_statistics(), patch(
            PATCH_ACCOUNT_LINKEDIN.format("_get_posts"),
            autospec=True,
            return_value=[],
        ) as mock_get_posts:
            self.assertFalse(self.SocialAccount._run_check_media_updates())
        self.assertTrue(
            mock_get_posts.called,
            msg="The stored value did not read as a baseline: the check "
            "reseeded instead of comparing.",
        )
        self.assertFalse(self.SocialAccountLinkedin.posts_need_import)
        self.assertEqual(
            self.SocialAccountLinkedin.linkedin_statistics_checkpoint,
            stored,
            msg="A mark that still matches is left as it was.",
        )

    def test_run_check_media_updates_ignores_an_unusable_mark(self):
        """A mark written by an older version is no baseline, and reseeds."""
        self._isolate_linkedin_account()
        self.SocialAccountLinkedin.linkedin_statistics_checkpoint = (
            '{"clickCount": 25, "likeCount": 12}'
        )
        with self._patch_recent_statistics(), patch(
            PATCH_ACCOUNT_LINKEDIN.format("_get_posts"), autospec=True
        ) as mock_get_posts:
            self.assertFalse(self.SocialAccount._run_check_media_updates())
        self.assertEqual(
            self.SocialAccountLinkedin.linkedin_statistics_checkpoint,
            self.SocialAccountLinkedin._linkedin_statistics_checkpoint(
                RECENT_STATISTICS_LINKEDIN
            ),
        )
        self.assertFalse(self.SocialAccountLinkedin.posts_need_import)
        mock_get_posts.assert_not_called()

    def test_run_check_media_updates_when_the_page_moved(self):
        """A page that moved is enough: the feed is not even asked for."""
        self._isolate_linkedin_account()
        self._mark_the_page_as_imported()
        mark = self.SocialAccountLinkedin.linkedin_statistics_checkpoint
        moved = {**RECENT_STATISTICS_LINKEDIN, _linkedin_day(1): (0, 2, 0, 0, 0)}
        with self._patch_recent_statistics(moved), patch(
            PATCH_ACCOUNT_LINKEDIN.format("_get_posts"), autospec=True
        ) as mock_get_posts:
            self.assertTrue(self.SocialAccount._run_check_media_updates())
        self.assertTrue(self.SocialAccountLinkedin.posts_need_import)
        mock_get_posts.assert_not_called()
        self.assertEqual(
            self.SocialAccountLinkedin.linkedin_statistics_checkpoint,
            mark,
            msg="The mark belongs to the import, so the notice does not "
            "clear itself on the next run.",
        )

    def test_run_check_media_updates_notices_the_impressions_alone(self):
        """Views with no interaction are an update too."""
        self._isolate_linkedin_account()
        self._mark_the_page_as_imported()
        moved = {**RECENT_STATISTICS_LINKEDIN, _linkedin_day(2): (5, 0, 0, 0, 30)}
        with self._patch_recent_statistics(moved):
            self.SocialAccount._run_check_media_updates()
        self.assertTrue(self.SocialAccountLinkedin.posts_need_import)

    def test_run_check_media_updates_notices_a_new_day_with_activity(self):
        """A day LinkedIn had nothing for before, now carrying activity."""
        self._isolate_linkedin_account()
        self._mark_the_page_as_imported()
        moved = {**RECENT_STATISTICS_LINKEDIN, _linkedin_day(0): (0, 1, 0, 0, 0)}
        with self._patch_recent_statistics(moved):
            self.SocialAccount._run_check_media_updates()
        self.assertTrue(self.SocialAccountLinkedin.posts_need_import)

    def test_run_check_media_updates_ignores_an_empty_new_day(self):
        """The day in progress starts as a bucket of zeros, not as news."""
        self._isolate_linkedin_account()
        self._mark_the_page_as_imported()
        quiet = {**RECENT_STATISTICS_LINKEDIN, _linkedin_day(0): (0, 0, 0, 0, 0)}
        with self._patch_recent_statistics(quiet), patch(
            PATCH_ACCOUNT_LINKEDIN.format("_get_posts"),
            autospec=True,
            return_value=[{"id": self.SocialPostAccountLinkedin.remote_ref}],
        ):
            self.assertFalse(self.SocialAccount._run_check_media_updates())
        self.assertFalse(self.SocialAccountLinkedin.posts_need_import)

    def test_run_check_media_updates_ignores_a_day_that_aged_out(self):
        """The window slides, so its oldest day leaving is not activity."""
        self._isolate_linkedin_account()
        self._mark_the_page_as_imported()
        slid = {
            period: figures
            for period, figures in RECENT_STATISTICS_LINKEDIN.items()
            if period != _linkedin_day(3)
        }
        with self._patch_recent_statistics(slid), patch(
            PATCH_ACCOUNT_LINKEDIN.format("_get_posts"),
            autospec=True,
            return_value=[{"id": self.SocialPostAccountLinkedin.remote_ref}],
        ):
            self.assertFalse(self.SocialAccount._run_check_media_updates())
        self.assertFalse(self.SocialAccountLinkedin.posts_need_import)

    def test_run_check_media_updates_without_posts(self):
        self._isolate_linkedin_account()
        self._mark_the_page_as_imported()
        with self._patch_recent_statistics(), patch(
            PATCH_ACCOUNT_LINKEDIN.format("_get_posts"),
            autospec=True,
            return_value=[],
        ) as mock_get_posts:
            self.assertFalse(self.SocialAccount._run_check_media_updates())
        self.assertTrue(mock_get_posts.called)
        self.assertFalse(self.SocialAccountLinkedin.posts_need_import)

    def test_run_check_media_updates_with_a_known_post(self):
        """Same figures and nothing new published: nothing to announce."""
        self._isolate_linkedin_account()
        self._mark_the_page_as_imported()
        with self._patch_recent_statistics(), patch(
            PATCH_ACCOUNT_LINKEDIN.format("_get_posts"),
            autospec=True,
            return_value=[{"id": self.SocialPostAccountLinkedin.remote_ref}],
        ):
            self.assertFalse(self.SocialAccount._run_check_media_updates())
        self.assertFalse(self.SocialAccountLinkedin.posts_need_import)

    def test_run_check_media_updates_sees_an_archived_publication(self):
        """Archiving a post does not make its publication new again."""
        self._isolate_linkedin_account()
        self._mark_the_page_as_imported()
        self.SocialPostAccountLinkedin.active = False
        with self._patch_recent_statistics(), patch(
            PATCH_ACCOUNT_LINKEDIN.format("_get_posts"),
            autospec=True,
            return_value=[
                {
                    "id": self.SocialPostAccountLinkedin.with_context(
                        active_test=False
                    ).remote_ref
                }
            ],
        ):
            self.assertFalse(self.SocialAccount._run_check_media_updates())
        self.assertFalse(self.SocialAccountLinkedin.posts_need_import)

    def test_run_check_media_updates_with_unknown_post(self):
        """A publication posted outside Odoo moves no figure of its own."""
        self._isolate_linkedin_account()
        self._mark_the_page_as_imported()
        with self._patch_recent_statistics(), patch(
            PATCH_ACCOUNT_LINKEDIN.format("_get_posts"),
            autospec=True,
            return_value=[{"id": "urn:li:share:not-imported-yet"}],
        ):
            self.SocialAccount._run_check_media_updates()
        self.assertTrue(self.SocialAccountLinkedin.posts_need_import)

    def test_run_check_media_updates_skips_a_flagged_account(self):
        """An account already announcing updates is not checked again."""
        self._isolate_linkedin_account()
        self._mark_the_page_as_imported()
        self.SocialAccountLinkedin.posts_need_import = True
        with self._patch_recent_statistics() as mock_reader, patch(
            PATCH_SYNC_ACCOUNT_LINKEDIN.format("_check_linkedin_updates"), autospec=True
        ) as mock_check, patch(
            PATCH_ACCOUNT_LINKEDIN.format("_get_posts"), autospec=True
        ) as mock_get_posts:
            self.assertFalse(self.SocialAccount._run_check_media_updates())
        mock_check.assert_not_called()
        mock_get_posts.assert_not_called()
        self.assertEqual(
            mock_reader.call_count,
            1,
            msg="Only the sweep asks: the flag says the user has an import "
            "pending, not that the figures of the page stopped moving.",
        )

    def test_run_check_media_updates_skips_an_account_without_organization(self):
        """The feed of an account with no organization cannot be asked for."""
        self._isolate_linkedin_account()
        self._mark_the_page_as_imported()
        self.SocialAccountLinkedin.remote_ref = False
        self.assertFalse(self.SocialAccountLinkedin.linkedin_account_id)
        with self._patch_recent_statistics() as mock_statistics, patch(
            PATCH_ACCOUNT_LINKEDIN.format("_get_posts"), autospec=True
        ) as mock_get_posts:
            self.assertFalse(self.SocialAccount._run_check_media_updates())
        mock_statistics.assert_not_called()
        mock_get_posts.assert_not_called()

    def test_run_check_media_updates_scans_every_account(self):
        """A flagged account must not stop the scan of the remaining ones."""
        self._isolate_linkedin_account()
        other_account = self.SocialAccountLinkedin.copy(
            {
                "name": "Other LinkedIn",
                "username": "other-linkedin",
                "remote_ref": "urn:li:organization:other",
            }
        )
        self._mark_the_page_as_imported(self.SocialAccountLinkedin | other_account)
        moved = {**RECENT_STATISTICS_LINKEDIN, _linkedin_day(1): (0, 2, 0, 0, 0)}
        with self._patch_recent_statistics(moved):
            self.SocialAccount._run_check_media_updates()
        self.assertTrue(self.SocialAccountLinkedin.posts_need_import)
        self.assertTrue(other_account.posts_need_import)

    @mute_logger(LOGGER_ACCOUNT_LINKEDIN, LOGGER_ACCOUNT_SYNC_LINKEDIN)
    def test_run_check_media_updates_isolates_each_account(self):
        """The account LinkedIn refused must not hide the others."""
        self._isolate_linkedin_account()
        failing = self.SocialAccountLinkedin
        working = failing.copy(
            {
                "name": "Other LinkedIn",
                "username": "other-linkedin",
                "remote_ref": "urn:li:organization:other",
            }
        )
        self._mark_the_page_as_imported(failing | working)

        def recent_statistics(account):
            if account.id == failing.id:
                raise UserError(_("LinkedIn refused the page statistics"))
            return {**RECENT_STATISTICS_LINKEDIN, _linkedin_day(1): (0, 2, 0, 0, 0)}

        with self._patch_recent_statistics(side_effect=recent_statistics):
            self.assertTrue(self.SocialAccount._run_check_media_updates())
        self.assertFalse(failing.posts_need_import)
        self.assertTrue(working.posts_need_import)

    @mute_logger(LOGGER_ACCOUNT_LINKEDIN, LOGGER_ACCOUNT_SYNC_LINKEDIN)
    def test_run_check_media_updates_reraises_a_concurrency_error(self):
        """Odoo keeps its retry: neither handler may swallow the error.

        The inner one re-raises it and the outer one has to let it through,
        because a cron gets no retry of its own.
        """

        class ConcurrencyError(psycopg2.OperationalError):
            pgcode = errorcodes.SERIALIZATION_FAILURE

        self._isolate_linkedin_account()
        self._mark_the_page_as_imported()
        with self._patch_recent_statistics(
            side_effect=ConcurrencyError("serialization conflict")
        ):
            with self.assertRaises(psycopg2.OperationalError):
                self.SocialAccount._run_check_media_updates()

    def test_run_check_media_updates_notifies_the_responsible_user(self):
        self._isolate_linkedin_account()
        self._mark_the_page_as_imported()
        Bus = self.env["bus.bus"]
        with self._patch_recent_statistics(), patch(
            PATCH_ACCOUNT_LINKEDIN.format("_get_posts"),
            autospec=True,
            return_value=[{"id": "urn:li:share:not-imported-yet"}],
        ), patch.object(type(Bus), "_sendone", autospec=True) as patch_sendone:
            self.SocialAccount._run_check_media_updates()
        patch_sendone.assert_called_once()
        self.assertEqual(
            patch_sendone.call_args[0][1],
            self.SocialAccountLinkedin.user_id.partner_id,
        )

    def test_run_check_media_updates_asks_the_finder_once_per_account(self):
        """The check compares what the sweep of the same pass already read."""
        self._isolate_linkedin_account()
        self._mark_the_page_as_imported()
        with self._patch_recent_statistics() as mock_reader, patch(
            PATCH_ACCOUNT_LINKEDIN.format("_get_posts"),
            autospec=True,
            return_value=[{"id": self.SocialPostAccountLinkedin.remote_ref}],
        ):
            self.assertFalse(self.SocialAccount._run_check_media_updates())
        self.assertEqual(
            mock_reader.call_count,
            1,
            msg="The sweep and the check used to ask the same finder for the "
            "same days, a few milliseconds apart.",
        )

    def test_run_check_media_updates_asks_the_finder_once_per_each_account(self):
        """Three eligible accounts, three calls: one apiece and no more."""
        self._isolate_linkedin_account()
        accounts = self.SocialAccountLinkedin
        for index in range(2):
            accounts |= self.SocialAccountLinkedin.copy(
                {
                    "name": f"Other LinkedIn {index}",
                    "username": f"other-linkedin-{index}",
                    "remote_ref": f"urn:li:organization:other-{index}",
                }
            )
        self._mark_the_page_as_imported(accounts)
        with self._patch_recent_statistics() as mock_reader, patch(
            PATCH_ACCOUNT_LINKEDIN.format("_get_posts"),
            autospec=True,
            return_value=[],
        ):
            self.assertFalse(self.SocialAccount._run_check_media_updates())
        self.assertEqual(mock_reader.call_count, len(accounts))

    @mute_logger(LOGGER_ACCOUNT_LINKEDIN, LOGGER_ACCOUNT_SYNC_LINKEDIN)
    def test_run_check_media_updates_skips_the_check_of_a_failed_sweep(self):
        """An account whose reading failed is not asked twice to fail twice."""
        self._isolate_linkedin_account()
        self._mark_the_page_as_imported()
        with self._patch_recent_statistics(
            side_effect=UserError(_("LinkedIn refused the page statistics"))
        ) as mock_reader, patch(
            PATCH_ACCOUNT_LINKEDIN.format("_get_posts"), autospec=True
        ) as mock_get_posts:
            self.assertFalse(self.SocialAccount._run_check_media_updates())
        self.assertEqual(mock_reader.call_count, 1)
        mock_get_posts.assert_not_called()
        self.assertFalse(
            self.SocialAccountLinkedin.posts_need_import,
            msg="A reading that failed says nothing about the page.",
        )

    def test_run_check_media_updates_keeps_a_stored_checkpoint_valid(self):
        """The day the sweep adds is not read as a day that appeared.

        The checkpoints already stored were written with the days the check
        compares. Comparing them against the wider window of the sweep would
        flag every active account at once on the first pass after deploying.
        """
        self._isolate_linkedin_account()
        self._mark_the_page_as_imported()
        eighth_day = (
            fields.Date.today() - timedelta(days=_UPDATE_CHECK_DAYS_LINKEDIN)
        ).isoformat()
        with self._patch_recent_statistics(
            {**RECENT_STATISTICS_LINKEDIN, eighth_day: (7, 7, 7, 7, 77)}
        ), patch(
            PATCH_ACCOUNT_LINKEDIN.format("_get_posts"),
            autospec=True,
            return_value=[{"id": self.SocialPostAccountLinkedin.remote_ref}],
        ):
            self.assertFalse(self.SocialAccount._run_check_media_updates())
        self.assertFalse(self.SocialAccountLinkedin.posts_need_import)

    def test_flag_linkedin_update_is_idempotent(self):
        """The bus message is not pushed again for what is already announced."""
        self.SocialAccountLinkedin.posts_need_import = True
        with patch(
            PATCH_SYNC_ACCOUNT.format("_notify_posts_need_import"), autospec=True
        ) as mock_notify:
            self.SocialAccountLinkedin._flag_linkedin_update()
        mock_notify.assert_not_called()

    def test_flag_linkedin_update_leaves_the_credentials_alone(self):
        """The two states are separate: this one says nothing about the token.

        An account whose credentials work is exactly the one that has
        publications to bring in, so announcing an import must not ask the
        user for a new authorization.
        """
        self.SocialAccountLinkedin.posts_need_import = False
        self.SocialAccountLinkedin.need_update = False
        self.SocialAccountLinkedin._flag_linkedin_update()
        self.assertTrue(self.SocialAccountLinkedin.posts_need_import)
        self.assertFalse(self.SocialAccountLinkedin.need_update)

    def test_flag_credentials_expired_leaves_the_import_alone(self):
        """And the other way round: expired credentials import nothing."""
        self.SocialAccountLinkedin.posts_need_import = False
        self.SocialAccountLinkedin._flag_credentials_expired("LinkedIn said no")
        self.assertTrue(self.SocialAccountLinkedin.need_update)
        self.assertFalse(self.SocialAccountLinkedin.posts_need_import)

    def test_a_new_authorization_leaves_the_import_alone(self):
        """Authorizing again resolves the credentials and nothing else."""
        self.SocialAccountLinkedin.write(
            {"need_update": True, "posts_need_import": True}
        )
        self.SocialAccountLinkedin._clear_credentials_flag()
        self.assertFalse(self.SocialAccountLinkedin.need_update)
        self.assertTrue(self.SocialAccountLinkedin.posts_need_import)

    def test_an_import_leaves_the_credentials_alone(self):
        """And the import resolves the publications and nothing else."""
        self.SocialAccountLinkedin.write(
            {"need_update": True, "posts_need_import": True}
        )
        self.SocialAccountLinkedin._clear_posts_need_import()
        self.assertFalse(self.SocialAccountLinkedin.posts_need_import)
        self.assertTrue(self.SocialAccountLinkedin.need_update)

    def test_run_check_media_updates_skips_expired_credentials(self):
        """A call made with a token known to be dead is a call thrown away.

        It could only end in a ``SocialCredentialsError``, and what the
        account is waiting for is a new authorization and not an import. The
        check used to skip it by accident, because both states shared a field.
        """
        self._isolate_linkedin_account()
        self._mark_the_page_as_imported()
        self.SocialAccountLinkedin.need_update = True
        moved = {**RECENT_STATISTICS_LINKEDIN, _linkedin_day(1): (0, 2, 0, 0, 0)}
        with self._patch_recent_statistics(moved), patch(
            PATCH_SYNC_ACCOUNT_LINKEDIN.format("_check_linkedin_updates"), autospec=True
        ) as mock_check, patch(
            PATCH_ACCOUNT_LINKEDIN.format("_get_posts"), autospec=True
        ) as mock_get_posts:
            self.assertFalse(self.SocialAccount._run_check_media_updates())
        mock_check.assert_not_called()
        mock_get_posts.assert_not_called()
        self.assertFalse(self.SocialAccountLinkedin.posts_need_import)

    def test_detects_pending_posts(self):
        """LinkedIn says the page moved without the publications being read."""
        self.assertTrue(self.SocialAccountLinkedin._detects_pending_posts())

    @mute_logger(LOGGER_ACCOUNT_LINKEDIN, LOGGER_ACCOUNT_SYNC_LINKEDIN)
    def test_run_check_media_updates_exception(self):
        self._isolate_linkedin_account()
        self._mark_the_page_as_imported()
        with self._patch_recent_statistics(), patch(
            PATCH_ACCOUNT_LINKEDIN.format("_get_posts"),
            autospec=True,
            side_effect=Exception("Error Check Media Updates"),
        ):
            self.assertFalse(self.SocialAccount._run_check_media_updates())
        self.assertFalse(self.SocialAccountLinkedin.posts_need_import)

    def test_linkedin_statistics_checkpoint_without_figures(self):
        """A reading that brought nothing is no baseline to compare with."""
        self.assertFalse(self.SocialAccountLinkedin._linkedin_statistics_checkpoint({}))

    def test_linkedin_statistics_moved_without_a_baseline(self):
        """Nothing to compare against announces nothing.

        The first reading of an account is the one that seeds the mark, and
        reporting it as movement would flag every account on the pass that
        follows deploying the module.
        """
        self.assertFalse(
            self.SocialAccountLinkedin._linkedin_statistics_moved(
                {}, RECENT_STATISTICS_LINKEDIN
            )
        )

    def test_detects_pending_posts_of_another_media(self):
        """An account of another network answers what its connector says."""
        self.assertFalse(self.social_account_id._detects_pending_posts())
