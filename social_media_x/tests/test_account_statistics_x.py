# Copyright 2026 Binhex <https://www.binhex.cloud>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from unittest.mock import MagicMock, patch

from freezegun import freeze_time

from odoo.tests.common import tagged
from odoo.tools import mute_logger

from ..social_x_utils import _GET_POSTS_MAX_IDS_X
from .test_common_x import TestSocialCommonX

LOGGER_ACCOUNT_BASE = "odoo.addons.social_media_base.models.social_account"
LOGGER_ACCOUNT_X = "odoo.addons.social_media_x.models.social_account"


@tagged("post_install", "-at_install")
class TestXPostStatistics(TestSocialCommonX):
    """The figures X reports for a publication, read by batches of ids.

    Nothing walks the timeline here: Odoo already knows the identifier of what
    it published, so one call answers a hundred posts.
    """

    def _post(self, ref, account=None, **values):
        """Create a publication of an X account, online and referenced."""
        return self.SocialPostAccount.create(
            dict(
                {
                    "message": "Test Message",
                    "account_id": (account or self.SocialAccountX).id,
                    "media_id": self.media_x_id.id,
                    "post_id": self.SocialPostX.id,
                    "remote_ref": ref,
                    "state": "posted",
                },
                **values,
            )
        )

    def _fake_post(self, ref, **metrics):
        """Return a post as tweepy answers it, with its metrics block."""
        answered = MagicMock()
        answered.id = ref
        answered.public_metrics = {
            "like_count": 0,
            "impression_count": 0,
            "reply_count": 0,
            "retweet_count": 0,
            "quote_count": 0,
            **metrics,
        }
        return answered

    def _fake_client(self, posts):
        """Return a tweepy client answering these posts to ``get_tweets``."""
        client = MagicMock()
        client.get_tweets.return_value = MagicMock(data=posts)
        return client

    def test_get_public_metrics(self):
        metrics = self._fake_post(
            "1",
            like_count=5,
            reply_count=10,
            retweet_count=15,
            quote_count=20,
            impression_count=40,
        )
        res = self.SocialAccountX._get_public_metrics(metrics)
        self.assertEqual(res, (5, 40, 10, 15, 20))

    def test_the_statistics_values_give_the_engagement(self):
        """Interactions over impressions, as a ratio from 0 to 1.

        One like, one reply and one repost in six impressions read 0.5, not 50.
        """
        values = self.SocialAccountX._x_statistics_values((1, 6, 1, 1, 0))
        self.assertEqual(values["engagement"], 0.5)

    def test_the_engagement_without_impressions_is_zero(self):
        """A post nobody saw yet has no rate, and no division by zero."""
        values = self.SocialAccountX._x_statistics_values((3, 0, 1, 0, 0))
        self.assertEqual(values["engagement"], 0)

    def test_refresh_post_statistics_writes_what_x_answered(self):
        """The metrics of the answer land on the line, with the date read.

        Retweets and quotes among them: they are figures of X the connector
        fills in, with or without a synchronization module.
        """
        line = self._post("1")
        client = self._fake_client(
            [
                self._fake_post(
                    "1",
                    like_count=5,
                    reply_count=10,
                    retweet_count=15,
                    quote_count=20,
                    impression_count=40,
                )
            ]
        )
        with patch.object(
            type(self.SocialAccountX),
            "get_client_api",
            autospec=True,
            return_value=client,
        ):
            refreshed = self.SocialAccountX._refresh_post_statistics(line)
        self.assertEqual(refreshed, line)
        self.assertEqual(line.like_count, 5)
        self.assertEqual(line.comment_count, 10)
        self.assertEqual(line.retweet_count, 15)
        self.assertEqual(line.quote_count, 20)
        self.assertEqual(line.impression_count, 40)
        self.assertEqual(line.engagement, (5 + 10 + 15 + 20) / 40)
        self.assertTrue(line.statistics_date)

    def test_a_hundred_ids_travel_in_one_call(self):
        """The ids are asked for in batches of what X answers at once."""
        refs = [str(index) for index in range(_GET_POSTS_MAX_IDS_X + 10)]
        lines = self.SocialPostAccount.union(*[self._post(ref) for ref in refs])
        client = self._fake_client([])
        with patch.object(
            type(self.SocialAccountX),
            "get_client_api",
            autospec=True,
            return_value=client,
        ):
            self.SocialAccountX._refresh_post_statistics(lines)
        self.assertEqual(client.get_tweets.call_count, 2)
        first, second = client.get_tweets.call_args_list
        self.assertEqual(len(first.kwargs["ids"]), _GET_POSTS_MAX_IDS_X)
        self.assertEqual(len(second.kwargs["ids"]), 10)

    def test_a_post_x_did_not_report_is_left_alone(self):
        """A post missing from the answer keeps the figures it already had.

        Unlike a figure of zero, silence about a post is a reading that did not
        happen: it may be deleted or hidden, and its line is not touched.
        """
        unreported = self._post("1", like_count=4)
        answered = self._post("2")
        client = self._fake_client([self._fake_post("2", like_count=8)])
        with patch.object(
            type(self.SocialAccountX),
            "get_client_api",
            autospec=True,
            return_value=client,
        ):
            refreshed = self.SocialAccountX._refresh_post_statistics(
                unreported + answered
            )
        self.assertEqual(refreshed, answered)
        self.assertEqual(unreported.like_count, 4)
        self.assertFalse(unreported.statistics_date)
        self.assertEqual(answered.like_count, 8)

    def test_the_exhausted_rate_limit_window_spends_no_call(self):
        """With the window of ``get_posts`` still open, nothing is asked.

        The quota of X is counted per endpoint and per window, so the pass
        leaves the account for the next run instead of failing, and the lines
        keep what they have.
        """
        line = self._post("1", like_count=4)
        client = self._fake_client([self._fake_post("1", like_count=9)])
        with patch.object(
            type(self.SocialAccountX),
            "get_client_api",
            autospec=True,
            return_value=client,
        ), patch.object(
            type(self.SocialAccountX),
            "_valid_time_request",
            autospec=True,
            return_value=False,
        ) as mock_valid:
            refreshed = self.SocialAccountX._refresh_post_statistics(line)
        client.get_tweets.assert_not_called()
        self.assertEqual(mock_valid.call_args.kwargs["endpoint"], "get_posts")
        self.assertFalse(refreshed)
        self.assertEqual(line.like_count, 4)
        self.assertFalse(line.statistics_date)

    def test_the_limit_reached_mid_pass_keeps_what_was_read(self):
        """The calls already spent are worth their figures.

        The batch that answered is written and the account is told when to
        retry; the posts of the batches left keep what they had.
        """
        first_batch = [str(index) for index in range(_GET_POSTS_MAX_IDS_X)]
        lines = self.SocialPostAccount.union(
            *[self._post(ref) for ref in [*first_batch, "late"]]
        )
        client = MagicMock()
        client.get_tweets.side_effect = [
            MagicMock(data=[self._fake_post("0", like_count=3)]),
            self.get_exception_manyrequests(),
        ]
        with patch.object(
            type(self.SocialAccountX),
            "get_client_api",
            autospec=True,
            return_value=client,
        ), patch.object(
            type(self.SocialAccountX),
            "_get_message_many_requests",
            autospec=True,
            return_value=False,
        ) as mock_warning:
            refreshed = self.SocialAccountX._refresh_post_statistics(lines)
        self.assertEqual(refreshed.mapped("remote_ref"), ["0"])
        self.assertEqual(mock_warning.call_args.kwargs["endpoint"], "get_posts")

    def test_refresh_post_statistics_leaves_another_media_alone(self):
        """A line of another social media is handed to the next connector."""
        posts_x = self._post("1")
        other = self.social_post_account_id
        client = self._fake_client([])
        with patch.object(
            type(self.SocialAccountX),
            "get_client_api",
            autospec=True,
            return_value=client,
        ):
            refreshed = self.SocialAccountX._refresh_post_statistics(posts_x + other)
        self.assertEqual(client.get_tweets.call_args.kwargs["ids"], ["1"])
        self.assertNotIn(other, refreshed)
        self.assertFalse(other.statistics_date)

    @mute_logger(LOGGER_ACCOUNT_BASE, LOGGER_ACCOUNT_X)
    def test_an_account_that_fails_does_not_stop_the_next(self):
        """Each account is read in its own savepoint."""
        broken = self._post("1")
        working = self._post("2", account=self.SocialAccountCredentialX)

        def client_of(account, *args, **kwargs):
            if account == self.SocialAccountX:
                raise ValueError("X refused this account")
            return self._fake_client([self._fake_post("2", like_count=6)])

        with patch.object(
            type(self.SocialAccountX),
            "get_client_api",
            autospec=True,
            side_effect=client_of,
        ):
            accounts = self.SocialAccountX + self.SocialAccountCredentialX
            refreshed = accounts._refresh_post_statistics(broken + working)
        self.assertEqual(refreshed, working)
        self.assertFalse(broken.statistics_date)
        self.assertEqual(working.like_count, 6)

    def test_the_dialog_draws_the_reposts_and_the_quotes(self):
        """The two figures only X reports are drawn by its connector.

        The refresh fills them for the recent publications, so they are numbers
        with no synchronization module installed, and the dialog has to show
        them.
        """
        arch = self.SocialPostAccount.get_view(
            self.env.ref(
                "social_media_base.social_post_account_view_form_statistics"
            ).id
        )["arch"]
        self.assertIn('name="retweet_count"', arch)
        self.assertIn('name="quote_count"', arch)


@tagged("post_install", "-at_install")
class TestXDashboardUpdate(TestSocialCommonX):
    """What the *Update* button of the dashboard answers for X accounts.

    X reports no daily series, so the figures of the recent posts are all the
    button reads for them, and X answering for any of them is an update.
    """

    def _window_post(self, ref, account=None):
        """Create a publication of an X account inside the refresh window."""
        return self.SocialPostAccount.create(
            {
                "message": "Test Message",
                "account_id": (account or self.SocialAccountX).id,
                "media_id": self.media_x_id.id,
                "post_id": self.SocialPostX.id,
                "remote_ref": ref,
                "state": "posted",
                "published_date": "2026-09-25 10:00:00",
            }
        )

    def _patch_read_of_x(self, answer=True):
        """Patch the read of the figures, X answering for every line or none."""
        return patch.object(
            type(self.SocialAccountX),
            "_write_posts_metrics",
            autospec=True,
            side_effect=lambda account, lines: lines if answer else lines.browse(),
        )

    @freeze_time("2026-09-30 10:00:00")
    def test_a_recent_post_x_answered_for_is_an_update(self):
        self._window_post("1")
        with self._patch_read_of_x():
            self.assertTrue(self.SocialAccountX.refresh_dashboard_statistics())

    @freeze_time("2026-09-30 10:00:00")
    def test_no_post_in_the_window_is_no_update(self):
        """The post of the fixture was never stamped as published."""
        with self._patch_read_of_x() as mock_read:
            self.assertFalse(self.SocialAccountX.refresh_dashboard_statistics())
        mock_read.assert_not_called()

    @freeze_time("2026-09-30 10:00:00")
    def test_a_post_x_did_not_answer_for_is_no_update(self):
        self._window_post("1")
        with self._patch_read_of_x(answer=False) as mock_read:
            self.assertFalse(self.SocialAccountX.refresh_dashboard_statistics())
        mock_read.assert_called_once()

    @freeze_time("2026-09-30 10:00:00")
    def test_every_account_reads_its_window_once(self):
        """Called on no account, base reads the window of each X one once.

        Base takes the empty recordset as every account, so each window is
        read, and paid, a single time.
        """
        accounts_x = self.SocialAccountX + self.SocialAccountCredentialX
        (self.SocialAccount.search([]) - accounts_x).write({"active": False})
        self._window_post("1")
        self._window_post("2", account=self.SocialAccountCredentialX)
        with self._patch_read_of_x() as mock_read:
            self.assertTrue(self.SocialAccount.browse().refresh_dashboard_statistics())
        read_ids = sorted(call.args[0].id for call in mock_read.call_args_list)
        self.assertEqual(read_ids, sorted(accounts_x.ids))

    @freeze_time("2026-09-30 10:00:00")
    def test_another_media_goes_through_base_and_x_is_read_once(self):
        """The other social media answers for its series, and X is read once."""
        self._window_post("1")
        with self._patch_read_of_x(answer=False) as mock_read, patch.object(
            type(self.SocialAccountX),
            "_refresh_statistics",
            autospec=True,
            return_value=True,
        ) as mock_series:
            accounts = self.social_account_id + self.SocialAccountX
            self.assertTrue(accounts.refresh_dashboard_statistics())
        mock_series.assert_called_once()
        mock_read.assert_called_once()

    @freeze_time("2026-09-30 10:00:00")
    def test_the_card_is_recomputed_after_the_read(self):
        """The figures of the card come from the lines just written."""
        self._window_post("1")
        steps = []
        with patch.object(
            type(self.SocialAccountX),
            "_write_posts_metrics",
            autospec=True,
            side_effect=lambda account, lines: steps.append("read") or lines,
        ), patch.object(
            type(self.SocialAccountX),
            "_refresh_account_statistics",
            autospec=True,
            side_effect=lambda accounts: steps.append(accounts) or True,
        ):
            self.SocialAccountX.refresh_dashboard_statistics()
        self.assertEqual(steps, ["read", self.SocialAccountX])
