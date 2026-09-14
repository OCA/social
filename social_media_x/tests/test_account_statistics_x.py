# Copyright 2026 Binhex <https://www.binhex.cloud>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from unittest.mock import MagicMock, patch

from odoo.tests.common import tagged
from odoo.tools import mute_logger

from ..social_x_utils import _GET_POSTS_MAX_IDS_X
from .test_common_x import TestSocialCommonX

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

    @mute_logger(LOGGER_ACCOUNT_X)
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
