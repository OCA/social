# Copyright 2026 Binhex <https://www.binhex.cloud>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from datetime import date
from unittest.mock import patch

import psycopg2

from odoo.exceptions import AccessError
from odoo.tests.common import tagged
from odoo.tools import mute_logger

from .test_social_common import TestSocialMediaBaseCommon


class TestSocialAccountStatistics(TestSocialMediaBaseCommon):
    """The time series the graph view reads: one row per account and day."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Statistics = cls.env["social.account.statistics"]
        cls.day = date(2025, 1, 1)

    def _rows_of(self, account):
        return self.Statistics.search([("account_id", "=", account.id)])

    def test_only_one_row_per_account_and_day(self):
        """The database refuses a second row of the same account and day."""
        self.Statistics.create(
            {"account_id": self.social_account_id.id, "date": self.day}
        )
        with self.assertRaises(psycopg2.IntegrityError), mute_logger("odoo.sql_db"):
            with self.env.cr.savepoint():
                self.Statistics.create(
                    {"account_id": self.social_account_id.id, "date": self.day}
                )

    def test_the_same_day_of_another_account_is_allowed(self):
        other = self.SocialAccount.create(
            {"name": "Other", "media_id": self.social_media_id.id}
        )
        self.Statistics.create(
            {"account_id": self.social_account_id.id, "date": self.day}
        )
        self.Statistics.create({"account_id": other.id, "date": self.day})
        self.assertEqual(
            self.Statistics.search_count([("date", "=", self.day)]),
            2,
        )

    def test_the_rows_go_with_the_account(self):
        """Deleting an account takes its statistics with it."""
        account = self.SocialAccount.create(
            {"name": "Doomed", "media_id": self.social_media_id.id}
        )
        self.Statistics.create({"account_id": account.id, "date": self.day})
        account.unlink()
        self.assertFalse(self.Statistics.search([("date", "=", self.day)]))

    def test_write_statistics_rows_creates_one_row_per_day(self):
        rows = self.social_account_id._write_statistics_rows(
            {
                date(2025, 1, 1): {"impression_count": 10},
                "2025-01-02": {"impression_count": 20},
            }
        )
        self.assertEqual(len(rows), 2)
        self.assertEqual(
            sorted(self._rows_of(self.social_account_id).mapped("date")),
            [date(2025, 1, 1), date(2025, 1, 2)],
            msg="A date and an ISO string name the same day.",
        )

    def test_write_statistics_rows_is_idempotent(self):
        """Writing the same window twice leaves the same rows and figures."""
        statistics = {
            date(2025, 1, 1): {"impression_count": 10, "engagement": 0.5},
            date(2025, 1, 2): {"impression_count": 20, "engagement": 0.25},
        }
        self.social_account_id._write_statistics_rows(statistics)
        self.social_account_id._write_statistics_rows(statistics)
        rows = self._rows_of(self.social_account_id)
        self.assertEqual(len(rows), 2)
        self.assertEqual(sorted(rows.mapped("impression_count")), [10, 20])

    def test_write_statistics_rows_updates_in_place(self):
        """A second pass revises the figures without resetting the others."""
        self.social_account_id._write_statistics_rows(
            {self.day: {"impression_count": 10, "like_count": 2}}
        )
        self.social_account_id._write_statistics_rows(
            {self.day: {"impression_count": 99}}
        )
        row = self._rows_of(self.social_account_id)
        self.assertEqual(row.impression_count, 99)
        self.assertEqual(
            row.like_count,
            2,
            msg="A partial revision must not zero what it does not carry.",
        )

    def test_write_statistics_rows_without_statistics(self):
        rows = self.social_account_id._write_statistics_rows({})
        self.assertFalse(rows)
        self.assertEqual(rows._name, "social.account.statistics")
        self.assertFalse(self.social_account_id._write_statistics_rows(None))

    def test_write_statistics_rows_takes_one_account(self):
        other = self.SocialAccount.create(
            {"name": "Other", "media_id": self.social_media_id.id}
        )
        with self.assertRaises(ValueError):
            (self.social_account_id | other)._write_statistics_rows(
                {self.day: {"impression_count": 1}}
            )

    def test_the_account_fields_are_stored_on_the_row(self):
        """``media_id`` and ``user_id`` are copied so the rules can filter."""
        self.social_account_id._write_statistics_rows(
            {self.day: {"impression_count": 1}}
        )
        row = self._rows_of(self.social_account_id)
        self.assertEqual(row.media_id, self.social_account_id.media_id)
        self.assertEqual(row.user_id, self.social_account_id.user_id)
        self.assertEqual(row.company_id, self.social_account_id.company_id)

    def test_the_counters_are_added_up_and_the_engagement_averaged(self):
        """Engagement is a ratio: adding it up over days means nothing."""
        self.social_account_id._write_statistics_rows(
            {
                date(2025, 1, 1): {"impression_count": 10, "engagement": 0.4},
                date(2025, 1, 2): {"impression_count": 30, "engagement": 0.8},
            }
        )
        groups = self.Statistics.read_group(
            [("account_id", "=", self.social_account_id.id)],
            ["impression_count", "engagement"],
            [],
        )
        self.assertEqual(groups[0]["impression_count"], 40)
        self.assertAlmostEqual(groups[0]["engagement"], 0.6)

    def test_the_empty_periods_are_filled_by_the_core(self):
        """``fill_temporal`` draws the days with no row, no code of ours."""
        self.social_account_id._write_statistics_rows(
            {
                date(2025, 1, 1): {"impression_count": 10},
                date(2025, 1, 4): {"impression_count": 30},
            }
        )
        groups = self.Statistics.with_context(fill_temporal=True).read_group(
            [("account_id", "=", self.social_account_id.id)],
            ["impression_count"],
            ["date:day"],
            lazy=False,
        )
        self.assertEqual(len(groups), 4)

    def test_the_hooks_of_the_base_do_nothing(self):
        """Base is media agnostic: a connector is what fills the series."""
        self.assertIsNone(
            self.social_account_id._snapshot_statistics(self.day, self.day)
        )
        self.assertFalse(self.social_account_id._refresh_statistics())
        self.assertFalse(self._rows_of(self.social_account_id))

    def test_refresh_statistics_says_when_there_is_no_series(self):
        """A media reporting no figures by day says so instead of lying."""
        Bus = self.env["bus.bus"]
        with patch.object(type(Bus), "_sendone", autospec=True) as mock_sendone:
            self.social_account_id.action_refresh_statistics()
        self.assertEqual(mock_sendone.call_args[0][2], "social_form_info")


@tagged("post_install", "-at_install")
class TestSocialAccountStatisticsUsers(TestSocialMediaBaseCommon):
    """Users are created here, so every module has to be in the registry."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Statistics = cls.env["social.account.statistics"]
        cls.day = date(2025, 1, 1)
        cls.social_user = cls.env["res.users"].create(
            {
                "name": "Social user",
                "login": "social_user_statistics",
                "groups_id": [
                    (
                        6,
                        0,
                        [
                            cls.env.ref("base.group_user").id,
                            cls.env.ref("social_media_base.group_social_media_user").id,
                        ],
                    )
                ],
            }
        )
        cls.social_manager = cls.env["res.users"].create(
            {
                "name": "Social manager",
                "login": "social_manager_statistics",
                "groups_id": [
                    (
                        6,
                        0,
                        [
                            cls.env.ref("base.group_user").id,
                            cls.env.ref(
                                "social_media_base.group_social_media_manager"
                            ).id,
                        ],
                    )
                ],
            }
        )
        cls.own_account = cls.SocialAccount.create(
            {
                "name": "Own",
                "media_id": cls.social_media_id.id,
                "user_id": cls.social_user.id,
            }
        )
        cls.other_account = cls.SocialAccount.create(
            {
                "name": "Somebody else",
                "media_id": cls.social_media_id.id,
                "user_id": cls.env.ref("base.user_admin").id,
            }
        )
        for account in (cls.own_account, cls.other_account):
            account._write_statistics_rows({cls.day: {"impression_count": 1}})

    def test_a_user_only_sees_the_rows_of_his_own_accounts(self):
        visible = self.Statistics.with_user(self.social_user).search([])
        self.assertEqual(visible.account_id, self.own_account)

    def test_the_rule_filters_the_aggregation_too(self):
        """A group by must not leak the figures the search hides."""
        groups = self.Statistics.with_user(self.social_user).read_group(
            [], ["impression_count"], ["account_id"], lazy=False
        )
        self.assertEqual(len(groups), 1)
        self.assertEqual(groups[0]["account_id"][0], self.own_account.id)

    def test_a_manager_sees_every_row(self):
        visible = self.Statistics.with_user(self.social_manager).search([])
        self.assertIn(self.own_account, visible.account_id)
        self.assertIn(self.other_account, visible.account_id)

    def test_a_user_cannot_write_the_rows_himself(self):
        """Reading is all a user is granted: the rows are written with sudo."""
        row = self.Statistics.with_user(self.social_user).search(
            [("account_id", "=", self.own_account.id)]
        )
        with self.assertRaises(AccessError):
            row.write({"impression_count": 5})

    def test_a_user_refreshes_his_own_account_all_the_same(self):
        """The button writes with ``sudo``, so read-only access is enough."""
        rows = self.own_account.with_user(self.social_user)._write_statistics_rows(
            {date(2025, 1, 2): {"impression_count": 7}}
        )
        self.assertEqual(len(rows), 1)


@tagged("post_install", "-at_install")
class TestSocialAccountDashboardStatistics(TestSocialMediaBaseCommon):
    """The figures of the dashboard card, added up without asking anybody."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Statistics = cls.env["social.account.statistics"]
        cls.account = cls.social_account_id
        cls.account.post_account_ids.unlink()

    def _series_row(self, day, **values):
        return self.Statistics.create(
            dict({"account_id": self.account.id, "date": day}, **values)
        )

    def _publication(self, **values):
        return self.env["social.post.account"].create(
            dict(
                {
                    "post_id": self.social_post_id.id,
                    "account_id": self.account.id,
                    "message": "Imported",
                },
                **values,
            )
        )

    def test_the_series_is_aggregated_and_the_engagement_averaged(self):
        """The engagement is a ratio: two days at 0,02 and 0,04 make 0,03.

        Adding it up would answer 0,06, which is not a rate any day had.
        """
        self._series_row(date(2025, 1, 1), engagement=0.02, like_count=3)
        self._series_row(date(2025, 1, 2), engagement=0.04, like_count=7)
        self.assertTrue(self.account.compute_dashboard_statistics())
        self.assertEqual(self.account.engagement, 0.03)
        self.assertEqual(self.account.like_count, 10)

    def test_the_publications_answer_when_there_is_no_series(self):
        """A social media reporting nothing by day keeps what was imported."""
        self._publication(engagement=0.02, like_count=3)
        self._publication(engagement=0.04, like_count=7)
        self.assertTrue(self.account.compute_dashboard_statistics())
        self.assertEqual(self.account.engagement, 0.03)
        self.assertEqual(self.account.like_count, 10)

    def test_the_series_wins_over_the_publications(self):
        """Those rows are the figures of the page, not only of what Odoo sent."""
        self._series_row(date(2025, 1, 1), engagement=0.05, like_count=1)
        self._publication(engagement=0.5, like_count=99)
        self.account.compute_dashboard_statistics()
        self.assertEqual(self.account.engagement, 0.05)
        self.assertEqual(self.account.like_count, 1)

    def test_nothing_stored_leaves_the_account_alone(self):
        """No rows and no publications is not the same as figures at zero."""
        self.assertFalse(self.account.compute_dashboard_statistics())
        self.assertEqual(self.account.engagement, 0)
        self.assertEqual(self.account.like_count, 0)

    def test_computing_asks_the_social_media_for_nothing(self):
        """Opening the dashboard happens constantly, so it cannot cost a call."""
        self._series_row(date(2025, 1, 1), engagement=0.02)
        with patch.object(
            type(self.account), "_refresh_statistics", autospec=True
        ) as mock_refresh:
            self.account.compute_dashboard_statistics()
        mock_refresh.assert_not_called()

    def test_refreshing_asks_the_series_first_and_aggregates_after(self):
        """The card is drawn from those rows, so the other order draws stale ones."""
        calls = []

        def refresh(accounts):
            calls.append("refresh")
            return True

        def aggregate(accounts):
            calls.append("aggregate")
            return True

        with patch.object(
            type(self.account),
            "_refresh_statistics",
            autospec=True,
            side_effect=refresh,
        ), patch.object(
            type(self.account),
            "_refresh_account_statistics",
            autospec=True,
            side_effect=aggregate,
        ):
            self.assertTrue(self.account.refresh_dashboard_statistics())
        self.assertEqual(calls, ["refresh", "aggregate"])

    def test_refreshing_says_when_nothing_came_back(self):
        """Without a connector no social media reports figures by day."""
        self.assertFalse(self.account.refresh_dashboard_statistics())
