# Copyright 2026 Binhex <https://www.binhex.cloud>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from datetime import datetime
from unittest.mock import MagicMock, patch

import psycopg2
import pytz
from psycopg2 import errorcodes
from tweepy.errors import Unauthorized

from odoo import Command, _
from odoo.exceptions import UserError
from odoo.tools import mute_logger

from odoo.addons.social_media_sync.tests.test_social_sync_common import (
    PATCH_SYNC_ACCOUNT,
)

from ..models.social_account import SocialAccount as SocialAccountXSync
from .test_sync_x_common import LOGGER_ACCOUNT_X_SYNC, TestSocialSyncCommonX


class TestSocialSyncAccountX(TestSocialSyncCommonX):
    def test_get_users_tweets(self):
        fake_client = MagicMock()
        fake_client.get_users_tweets.return_value.includes = {
            "media": [self.image_base64]
        }
        patch_get_client_api = self.get_patch_exceptions_x(
            fake_client=fake_client, valid_time_request=False
        )
        with (
            patch_get_client_api as mock_get_client_api,
        ):
            res = self.SocialAccountX._get_users_tweets()
            self.assertEqual(len(res.includes.get("media")), 1)
        mock_get_client_api.assert_called_once()
        _, kwargs = fake_client.get_users_tweets.call_args
        self.assertEqual(kwargs["id"], self.SocialAccountX.remote_ref)
        self.assertEqual(kwargs["max_results"], 100)

    def test_get_x_statistics(self):
        statistics = ["Test", 1, 1, 10, 11, 12, 13]
        rows = [{"id": self.SocialAccountX.id, "name": "X Account"}]
        with patch(
            "odoo.models.BaseModel.search_read", autospec=True, return_value=rows
        ) as mock_search_read:
            res = self.SocialAccountX._get_x_statistics(statistics)
        mock_search_read.assert_called_once()
        self.assertEqual(res, statistics + rows)
        self.assertIn(("media_type", "=", "x"), mock_search_read.call_args.args[1])

    def test_update_posts_statistics(self):
        # The user reading the import is not in UTC, so a date stored in his
        # zone instead of UTC would differ from the one asserted below.
        self.env.user.tz = "Europe/Madrid"
        patch_super = patch(PATCH_SYNC_ACCOUNT.format("_update_posts_statistics"))
        patch_get_statistics = patch.object(
            type(self.SocialAccount),
            "_get_x_statistics",
            autospec=True,
            return_value=None,
        )
        fake_client = MagicMock()
        fake_client.get_users_tweets.return_value.includes = {
            "media": [
                MagicMock(
                    media_key="media_key_tests",
                    url="https://media_url_tests",
                    type="image",
                )
            ],
            "users": [MagicMock(id="author_12345", username="username-idx")],
        }
        # X answers the date with the offset of the tweet, not in UTC.
        tweet_created_at = pytz.timezone("Australia/Sydney").localize(
            datetime(2026, 1, 15, 21, 30)
        )
        fake_tweet = MagicMock(
            referenced_tweets=[MagicMock(type="fake_quoted")],
            in_reply_to_user_id=None,
            conversation_id="conversation_12345",
            id="conversation_12345",
            author_id="author_12345",
            text="Tweet text https://t.co/short",
            created_at=tweet_created_at,
            attachments={"media_keys": ["media_key_tests"]},
            entities={"urls": [{"url": "https://t.co/short"}]},
        )
        fake_tweet.get.return_value = "conversation_12345"
        fake_client.get_users_tweets.return_value.data = [fake_tweet]
        patch_get_users_tweets = self.get_patch_exceptions_x(
            fake_client=fake_client, valid_time_request=False
        )

        search_side_effect = self.get_search_side_effect_x()

        with (
            patch_super as mock_update_posts_statistics_super,
            patch(
                "odoo.models.BaseModel.search",
                autospec=True,
                side_effect=search_side_effect,
            ) as mock_search,
            patch.object(
                type(self.SocialAccount),
                "_valid_time_request",
                autospec=True,
                return_value=True,
            ) as mock_valid_time_request,
            patch.object(
                type(self.SocialPostAccountX),
                "_get_assets_save_x",
                autospec=True,
                side_effect=lambda self, *args, **kwargs: (
                    self.env["ir.attachment"].create(
                        {"name": "media_key_tests", "type": "binary"}
                    ),
                    {},
                ),
            ) as mock_get_assets_save_x,
            patch.object(
                type(self.SocialAccount),
                "_get_public_metrics",
                autospec=True,
                return_value=(5, 10, 15, 20, 25),
            ) as mock_get_public_metrics,
            patch_get_users_tweets as mock_get_users_tweets,
            patch_get_statistics as mock_get_statistics,
        ):
            self.SocialAccount._update_posts_statistics(None, [])

            mock_update_posts_statistics_super.assert_called_once()
            self.assertEqual(
                self._count_search_calls(
                    mock_search,
                    model="social.account",
                    domain_leaf=("media_type", "=", "x"),
                ),
                1,
                msg="One social.account search for the x media type.",
            )
            self.assertEqual(
                self._count_search_calls(
                    mock_search,
                    model="social.post.account",
                    domain_leaf=("remote_ref", "in", ["conversation_12345"]),
                ),
                1,
                msg="One search to prefetch the post accounts of the tweet.",
            )
            mock_valid_time_request.assert_called_once()
            mock_get_users_tweets.assert_called_once()
            mock_get_assets_save_x.assert_called_once()
            mock_get_public_metrics.assert_called_once()
            mock_get_statistics.assert_called_once()

        self.env.flush_all()
        self.env.invalidate_all()

        post_account = self.SocialAccountX.post_account_ids.filtered(
            lambda post: post.remote_ref == "conversation_12345"
        )
        self.assertEqual(len(post_account), 1)
        self.assertEqual(
            post_account.like_count,
            5,
            msg="Read back from the database so a silently swallowed write "
            "cannot make the assertions pass from the ORM cache.",
        )
        self.assertEqual(post_account.impression_count, 10)
        self.assertEqual(post_account.comment_count, 15)
        self.assertEqual(post_account.retweet_count, 20)
        self.assertEqual(post_account.quote_count, 25)
        self.assertEqual(post_account.message, "Tweet text ")
        self.assertEqual(
            self.SocialAccountX.read(
                ["like_count", "impression_count", "comment_count"]
            )[0],
            {
                "id": self.SocialAccountX.id,
                "like_count": 0,
                "impression_count": 0,
                "comment_count": 0,
            },
            msg="The import writes rows, not the aggregated figures of the "
            "account: those are derived by social_media_base.",
        )
        self.assertEqual(post_account.author, self.SocialAccountX.name)
        self.assertEqual(post_account.actor_urn, "author_12345")
        self.assertEqual(post_account.state, "posted")
        self.assertEqual(
            post_account.published_date,
            datetime(2026, 1, 15, 10, 30),
            msg="A Datetime is stored in UTC: the client is what converts it "
            "to the zone of whoever reads it.",
        )
        self.assertEqual(post_account.image_ids.mapped("name"), ["media_key_tests"])

    def test_import_updates_an_archived_line_instead_of_duplicating_it(self):
        """A tweet whose line is archived is reconciled, not imported again.

        The line is the only place holding ``remote_ref``, so a page read
        without the archived ones brings the same tweet in under a second
        publication.
        """
        line = self.SocialPostAccountX
        line.write({"remote_ref": "archived_tweet", "active": False})
        fake_client = MagicMock()
        fake_client.get_users_tweets.return_value.includes = {
            "users": [MagicMock(id="author_12345", username="username-idx")]
        }
        fake_tweet = MagicMock(
            referenced_tweets=None,
            in_reply_to_user_id=None,
            conversation_id="archived_tweet",
            id="archived_tweet",
            author_id="author_12345",
            text="Archived tweet text",
            created_at=datetime(2026, 3, 1, 8, 0, tzinfo=pytz.utc),
            attachments={},
            entities=None,
        )
        fake_tweet.get.return_value = "archived_tweet"
        fake_client.get_users_tweets.return_value.data = [fake_tweet]
        (
            patch_get_client_api,
            patch_valid_time_request,
        ) = self.get_patch_exceptions_x(fake_client=fake_client)
        with (
            patch(PATCH_SYNC_ACCOUNT.format("_update_posts_statistics")),
            patch_get_client_api,
            patch_valid_time_request,
            patch.object(
                type(self.SocialAccount),
                "_get_public_metrics",
                autospec=True,
                return_value=(0, 0, 0, 0, 0),
            ),
            patch.object(
                type(self.SocialAccount),
                "_get_x_statistics",
                autospec=True,
                return_value=None,
            ),
        ):
            self.SocialAccountX._update_posts_statistics(None, [], set())
        self.env.flush_all()
        self.env.invalidate_all()
        lines = self.SocialPostAccount.with_context(active_test=False).search(
            [
                ("remote_ref", "=", "archived_tweet"),
                ("account_id", "=", self.SocialAccountX.id),
            ]
        )
        self.assertEqual(lines, line, "The archived line is the one written.")
        self.assertEqual(lines.message, "Archived tweet text")

    def test_the_timeline_values_carry_no_aggregated_figures(self):
        """What the import writes on the account is the page, not its totals."""
        response = MagicMock()
        response.meta = {"newest_id": "tweet_1"}
        values = self.SocialAccountX._get_timeline_account_values(
            response, [Command.create({"message": "Imported"})]
        )
        self.assertEqual(sorted(values), ["last_post_ref", "post_account_ids"])

    def test_update_posts_statistics_reads_only_its_own_accounts(self):
        """A mixed recordset hands the timeline the X accounts alone.

        The tweets are read one account at a time, and the quota is spent per
        account, so an account of another social media travelling in the same
        recordset would spend a request of its own on a timeline that is not
        there.
        """
        mixed = self.SocialAccountX | self.social_account_id
        with patch.object(
            type(self.SocialAccount),
            "_valid_time_request",
            autospec=True,
            return_value=False,
        ) as mock_valid_time_request:
            mixed._update_posts_statistics(None, [])
        self.assertEqual(
            [call.args[0] for call in mock_valid_time_request.call_args_list],
            [self.SocialAccountX],
        )

    def test_update_posts_statistics_since_reads_from_the_publication(self):
        """With *Enable since* the timeline is asked from the stored publication.

        Reading a partial page is safe on its own terms now: the import writes
        the figures of each tweet on its publication and never the totals of
        the account, which base derives from those rows.
        """
        self.SocialAccountX.write(
            {
                "enable_since": True,
                "like_count": 100,
                "impression_count": 200,
                "comment_count": 300,
                "retweet_count": 400,
                "quote_count": 500,
            }
        )
        self.assertEqual(
            self.SocialAccountX.post_since_id,
            self.SocialPostAccountX,
            msg="The option has to resolve to a publication for since_id to be sent.",
        )

        patch_super = patch(PATCH_SYNC_ACCOUNT.format("_update_posts_statistics"))
        patch_get_statistics = patch.object(
            type(self.SocialAccount),
            "_get_x_statistics",
            autospec=True,
            return_value=None,
        )
        fake_client = MagicMock()
        fake_client.get_users_tweets.return_value.includes = {
            "media": [],
            "users": [MagicMock(id="author_12345", username="username-idx")],
        }
        fake_tweet = MagicMock(
            referenced_tweets=[],
            in_reply_to_user_id=None,
            conversation_id="tweet_since_1",
            id="tweet_since_1",
            author_id="author_12345",
            text="Newer tweet",
            created_at=datetime(2026, 2, 20, 9, 0, tzinfo=pytz.utc),
            attachments={},
            entities={},
        )
        fake_tweet.get.return_value = "tweet_since_1"
        fake_client.get_users_tweets.return_value.data = [fake_tweet]
        fake_client.get_users_tweets.return_value.meta = {"newest_id": "tweet_since_1"}
        patch_get_users_tweets = self.get_patch_exceptions_x(
            fake_client=fake_client, valid_time_request=False
        )

        with (
            patch_super,
            patch(
                "odoo.models.BaseModel.search",
                autospec=True,
                side_effect=self.get_search_side_effect_x(),
            ),
            patch.object(
                type(self.SocialAccount),
                "_valid_time_request",
                autospec=True,
                return_value=True,
            ),
            patch.object(
                type(self.SocialAccount),
                "_get_public_metrics",
                autospec=True,
                return_value=(1, 2, 3, 4, 5),
            ),
            patch_get_users_tweets,
            patch_get_statistics,
        ):
            self.SocialAccount._update_posts_statistics(None, [])
            self.assertEqual(
                fake_client.get_users_tweets.call_args.kwargs.get("since_id"),
                self.SocialPostAccountX.remote_ref,
                msg="The timeline has to be asked from the stored publication.",
            )

        self.env.flush_all()
        self.env.invalidate_all()
        self.assertEqual(self.SocialAccountX.like_count, 100)
        self.assertEqual(self.SocialAccountX.impression_count, 200)
        self.assertEqual(self.SocialAccountX.comment_count, 300)
        self.assertEqual(self.SocialAccountX.retweet_count, 400)
        self.assertEqual(self.SocialAccountX.quote_count, 500)
        self.assertEqual(self.SocialAccountX.last_post_ref, "tweet_since_1")
        self.assertEqual(
            self.SocialAccountX.post_account_ids.filtered(
                lambda post: post.remote_ref == "tweet_since_1"
            ).impression_count,
            2,
            msg="The figures of the tweet go on its publication, which is "
            "what base adds up.",
        )
        self.assertTrue(
            self.SocialAccountX.post_account_ids.filtered(
                lambda post: post.remote_ref == "tweet_since_1"
            ),
            msg="The publication itself still has to be stored.",
        )

    def test_update_posts_statistics_empty_page(self):
        """An empty answer is only an error when X reports one."""
        patch_super = patch(PATCH_SYNC_ACCOUNT.format("_update_posts_statistics"))
        patch_get_statistics = patch.object(
            type(self.SocialAccount),
            "_get_x_statistics",
            autospec=True,
            return_value=None,
        )
        fake_client = MagicMock()
        fake_client.get_users_tweets.return_value.data = None
        fake_client.get_users_tweets.return_value.errors = []
        patch_get_users_tweets = self.get_patch_exceptions_x(
            fake_client=fake_client, valid_time_request=False
        )

        patches = (
            patch(
                "odoo.models.BaseModel.search",
                autospec=True,
                side_effect=self.get_search_side_effect_x(),
            ),
            patch.object(
                type(self.SocialAccount),
                "_valid_time_request",
                autospec=True,
                return_value=True,
            ),
        )

        with (
            patch_super,
            patches[0],
            patches[1],
            patch.object(
                type(self.SocialAccount), "_notify_user_client", autospec=True
            ) as mock_notify,
            patch_get_users_tweets,
            patch_get_statistics,
        ):
            self.SocialAccount._update_posts_statistics(None, [])
            mock_notify.assert_not_called()

        fake_client.get_users_tweets.return_value.errors = [{"detail": "boom"}]
        with (
            patch_super,
            patches[0],
            patches[1],
            patch.object(
                type(self.SocialAccount), "_notify_user_client", autospec=True
            ) as mock_notify,
            patch_get_users_tweets,
            patch_get_statistics,
        ):
            self.SocialAccount._update_posts_statistics(None, [])
            mock_notify.assert_called_once()
            self.assertEqual(
                mock_notify.call_args.kwargs.get("notif_type"),
                "social_kanban_danger",
            )

    def test_update_posts_statistics_empty(self):
        patch_super = patch(PATCH_SYNC_ACCOUNT.format("_update_posts_statistics"))
        patch_get_statistics = patch.object(
            type(self.SocialAccount),
            "_get_x_statistics",
            autospec=True,
            return_value=None,
        )

        with (
            patch_super as mock_update_posts_statistics_super,
            patch_get_statistics as mock_get_statistics,
        ):
            self.social_account_id._update_posts_statistics(None, [])
            mock_update_posts_statistics_super.assert_called_once()
            mock_get_statistics.assert_called_once()

    @staticmethod
    def _report_imported(accounts, post_id, domain, imported):
        """Stand for an import that did read the accounts it was given."""
        imported.update(accounts.ids)
        return []

    def test_update_posts_statistics_inside_the_quota_window_is_not_an_import(self):
        """The window of the endpoint still open leaves the account unread.

        The figures answered here are the ones already stored, so they look
        the same whether the timeline was read or not: what tells them apart
        is that nothing is reported as imported.
        """
        patch_super = patch(PATCH_SYNC_ACCOUNT.format("_update_posts_statistics"))
        patch_get_statistics = patch.object(
            type(self.SocialAccount),
            "_get_x_statistics",
            autospec=True,
            return_value=None,
        )
        patch_client = self.get_patch_exceptions_x(
            fake_client=MagicMock(), valid_time_request=False
        )
        reported = set()
        with (
            patch_super,
            patch_client as mock_client,
            patch.object(
                type(self.SocialAccount),
                "_valid_time_request",
                autospec=True,
                return_value=False,
            ),
            patch_get_statistics,
        ):
            self.SocialAccountX._update_posts_statistics(None, [], reported)
        mock_client.assert_not_called()
        self.assertFalse(reported)

    @mute_logger(LOGGER_ACCOUNT_X_SYNC)
    def test_update_posts_statistics_rate_limited_is_not_an_import(self):
        """A timeline X refused for quota leaves the account unread."""
        patch_super = patch(PATCH_SYNC_ACCOUNT.format("_update_posts_statistics"))
        patch_get_statistics = patch.object(
            type(self.SocialAccount),
            "_get_x_statistics",
            autospec=True,
            return_value=None,
        )
        fake_client = MagicMock()
        fake_client.get_users_tweets.side_effect = self.get_exception_manyrequests()
        patch_client = self.get_patch_exceptions_x(
            fake_client=fake_client, valid_time_request=False
        )
        reported = set()
        with (
            patch_super,
            patch_client,
            patch.object(
                type(self.SocialAccount),
                "_valid_time_request",
                autospec=True,
                return_value=True,
            ),
            patch.object(
                type(self.SocialAccount),
                "_get_message_many_requests",
                autospec=True,
                return_value=False,
            ),
            patch_get_statistics,
        ):
            self.SocialAccountX._update_posts_statistics(None, [], reported)
        self.assertFalse(reported)

    def test_update_posts_statistics_reports_the_timeline_it_read(self):
        """An empty timeline is still a timeline that was read.

        X answering that nothing was published since the checkpoint is a good
        import with nothing to bring in, so the account does not need its
        first import run again.
        """
        patch_super = patch(PATCH_SYNC_ACCOUNT.format("_update_posts_statistics"))
        patch_get_statistics = patch.object(
            type(self.SocialAccount),
            "_get_x_statistics",
            autospec=True,
            return_value=None,
        )
        fake_client = MagicMock()
        fake_client.get_users_tweets.return_value.data = None
        fake_client.get_users_tweets.return_value.errors = []
        patch_client = self.get_patch_exceptions_x(
            fake_client=fake_client, valid_time_request=False
        )
        reported = set()
        with (
            patch_super,
            patch(
                "odoo.models.BaseModel.search",
                autospec=True,
                side_effect=self.get_search_side_effect_x(),
            ),
            patch.object(
                type(self.SocialAccount),
                "_valid_time_request",
                autospec=True,
                return_value=True,
            ),
            patch_client,
            patch_get_statistics,
        ):
            self.SocialAccountX._update_posts_statistics(None, [], reported)
        self.assertEqual(reported, set(self.SocialAccountX.ids))

    @mute_logger(LOGGER_ACCOUNT_X_SYNC)
    def test_update_posts_statistics_errors_are_not_an_import(self):
        """A page X answered with errors is not a timeline that was read."""
        patch_super = patch(PATCH_SYNC_ACCOUNT.format("_update_posts_statistics"))
        patch_get_statistics = patch.object(
            type(self.SocialAccount),
            "_get_x_statistics",
            autospec=True,
            return_value=None,
        )
        fake_client = MagicMock()
        fake_client.get_users_tweets.return_value.data = None
        fake_client.get_users_tweets.return_value.errors = [{"detail": "boom"}]
        patch_client = self.get_patch_exceptions_x(
            fake_client=fake_client, valid_time_request=False
        )
        reported = set()
        with (
            patch_super,
            patch(
                "odoo.models.BaseModel.search",
                autospec=True,
                side_effect=self.get_search_side_effect_x(),
            ),
            patch.object(
                type(self.SocialAccount),
                "_valid_time_request",
                autospec=True,
                return_value=True,
            ),
            patch.object(
                type(self.SocialAccount), "_notify_user_client", autospec=True
            ),
            patch_client,
            patch_get_statistics,
        ):
            self.SocialAccountX._update_posts_statistics(None, [], reported)
        self.assertFalse(reported)

    def test_x_check_updates_does_not_claim_an_import_it_skipped(self):
        """The check answers whether it ran, and a skipped import did not."""
        with patch.object(
            type(self.SocialAccount),
            "_update_posts_statistics",
            autospec=True,
            return_value=[],
        ):
            self.assertFalse(self.SocialAccountX._x_check_updates())

    def test_x_check_updates_imports_the_timeline(self):
        """The only endpoint that knows whether anything moved is the timeline.

        So the check does not flag the account for the user to import later:
        it imports, and answers that it ran.
        """
        with patch.object(
            type(self.SocialAccount),
            "_update_posts_statistics",
            autospec=True,
            side_effect=self._report_imported,
        ) as mock_import:
            self.assertTrue(self.SocialAccountX._x_check_updates())
        mock_import.assert_called_once()
        self.assertEqual(mock_import.call_args.args[0], self.SocialAccountX)

    def test_run_check_media_updates_imports_once_per_account(self):
        """The cron entry point reaches the import once for each X account."""
        accounts_x = self.SocialAccountX + self.SocialAccountCredentialX
        with patch.object(
            type(self.SocialAccount),
            "_get_check_media_updates_domain",
            autospec=True,
            return_value=[("id", "in", accounts_x.ids)],
        ), patch.object(
            type(self.SocialAccount),
            "_update_posts_statistics",
            autospec=True,
            side_effect=self._report_imported,
        ) as mock_import:
            self.assertTrue(self.SocialAccount._run_check_media_updates())
        self.assertEqual(mock_import.call_count, len(accounts_x))
        imported = self.SocialAccount.browse()
        for call in mock_import.call_args_list:
            imported |= call.args[0]
        self.assertEqual(imported, accounts_x)

    def test_onchange_post_since_id(self):
        self.SocialAccountX._onchange_post_since_id()
        self.assertFalse(self.SocialAccountX.post_since_id)
        self.assertFalse(self.SocialAccountX.last_post_ref)

    def test_compute_post_since_id(self):
        account_id = self.SocialAccount.create(
            {
                "name": "Test account X",
                "media_id": self.media_x_id.id,
                "enable_since": True,
            }
        )
        post_id = self.SocialPost.create(
            {
                "message": "Test Message Enable Since",
                "account_ids": [Command.set(account_id.ids)],
            }
        )
        post_account_values = {
            "post_id": post_id.id,
            "account_id": account_id.id,
            "message": "Message Test XX",
            "click_count": 5,
            "comment_count": 2,
            "retweet_count": 3,
            "quote_count": 2,
        }
        post_account_id = self.SocialPostAccount.create(post_account_values)
        self.assertEqual(account_id.post_since_id, post_account_id)

        account_id.write({"enable_since": False})
        self.assertFalse(
            account_id.post_since_id,
            msg="Turning the option off by write must clear the stored post.",
        )
        account_id.write({"enable_since": True})
        self.assertEqual(account_id.post_since_id, post_account_id)

        account_id.write({"last_post_ref": post_account_id.id})
        self.assertEqual(int(account_id.last_post_ref), post_account_id.id)

    def test_the_since_fields_arrive_with_this_module(self):
        """The checkpoint of the import belongs to whoever reads the timeline.

        Without a synchronization module the three of them mean nothing: the
        toggle would govern an import that does not exist.
        """
        for field_name in ("last_post_ref", "enable_since", "post_since_id"):
            field = self.SocialAccount._fields[field_name]
            self.assertEqual(
                field._module,
                "social_media_x_sync",
                msg=f"{field_name} has to be declared by this module.",
            )

    def test_the_account_form_shows_the_since_fields(self):
        """The view of the connector is the one this one inherits from.

        Applied over the arch its parent produced, so the group of the
        connector and its fields are there when this one is applied, and the
        four fields end up in the same group as before the split.
        """
        view = self.env.ref(
            "social_media_x_sync.social_account_view_form_inherit_sync_x"
        )
        self.assertEqual(
            view.inherit_id,
            self.env.ref("social_media_x.social_account_view_form_inherit"),
        )
        arch = self.SocialAccount.get_view(
            self.env.ref("social_media_base.social_account_view_form").id, "form"
        )["arch"]
        for field_name in ("x_api_secret", "enable_since", "post_since_id"):
            self.assertIn(f'name="{field_name}"', arch)

    def test_the_association_flags_the_first_import(self):
        """With the bridge installed, associating queues the initial sync."""
        account = self.SocialAccountX
        account.write({"pending_initial_sync": False})
        account._on_account_associated()
        self.assertTrue(
            account.pending_initial_sync,
            msg="The account has to wait for its first import before the "
            "bihourly check walks it.",
        )

    @mute_logger(LOGGER_ACCOUNT_X_SYNC)
    def test_x_check_updates_isolates_each_account(self):
        """The account X refused must not stop the ones still to come.

        The import writes as it goes, so each account runs in its own
        savepoint and a failure only undoes its own work.
        """
        failing = self.SocialAccountX
        working = self.SocialAccountCredentialX
        imported = []

        def import_posts(account, post_id, domain, reported):
            if account.id == failing.id:
                raise UserError(_("X refused the timeline"))
            imported.append(account.id)
            reported.add(account.id)

        with patch.object(
            type(self.SocialAccount),
            "_update_posts_statistics",
            autospec=True,
            side_effect=import_posts,
        ):
            self.assertTrue((failing + working)._x_check_updates())
        self.assertEqual(imported, working.ids)

    @mute_logger(LOGGER_ACCOUNT_X_SYNC)
    def test_x_check_updates_reraises_a_concurrency_error(self):
        """Odoo keeps its retry: the handler may not swallow the error."""

        class ConcurrencyError(psycopg2.OperationalError):
            pgcode = errorcodes.SERIALIZATION_FAILURE

        with patch.object(
            type(self.SocialAccount),
            "_update_posts_statistics",
            autospec=True,
            side_effect=ConcurrencyError("serialization conflict"),
        ), self.assertRaises(psycopg2.OperationalError):
            self.SocialAccountX._x_check_updates()

    def test_the_bridge_does_not_read_the_metrics_itself(self):
        """The reading of the metrics belongs to the connector.

        Two definitions of it are two readings that drift apart with the first
        change, so this module asks for the one of ``social_media_x``.
        """
        self.assertNotIn("_get_public_metrics", SocialAccountXSync.__dict__)
        self.assertTrue(hasattr(self.SocialAccountX, "_get_public_metrics"))

    def test_onchange_post_since_id_keeps_the_checkpoint_while_enabled(self):
        """The onchange clears the checkpoint only when the option goes off.

        An account that keeps *Enable since* on would otherwise be asked for
        its whole history again on the next import.
        """
        self.SocialAccountX.write({"enable_since": True})
        self.SocialAccountX.last_post_ref = "tweet_1"
        self.SocialAccountX._onchange_post_since_id()
        self.assertEqual(
            self.SocialAccountX.last_post_ref,
            "tweet_1",
            msg="The reference of the newest tweet read survives the onchange.",
        )

    def test_the_timeline_values_of_a_page_with_nothing_to_store(self):
        """A page whose tweets are all discarded still moves the checkpoint.

        Retweets, replies and quotes are read and thrown away, so a page made
        only of them writes no publication; asking for them again on the next
        import is what the checkpoint exists to avoid.
        """
        self.SocialAccountX.enable_since = True
        response = MagicMock()
        response.meta = {"newest_id": "tweet_1"}
        self.assertEqual(
            self.SocialAccountX._get_timeline_account_values(response, []),
            {"last_post_ref": "tweet_1"},
        )

    def test_update_posts_statistics_discards_what_the_account_did_not_write(self):
        """Only what the account published on its own becomes a publication.

        A reply and a quote travel in the same timeline as the tweets of the
        account, and neither is an editorial post of Odoo.
        """
        patch_super = patch(PATCH_SYNC_ACCOUNT.format("_update_posts_statistics"))
        patch_get_statistics = patch.object(
            type(self.SocialAccount),
            "_get_x_statistics",
            autospec=True,
            return_value=None,
        )
        reply = MagicMock(
            referenced_tweets=[MagicMock(type="replied_to")],
            in_reply_to_user_id="author_54321",
            conversation_id="conversation_54321",
            id="reply_12345",
        )
        quote = MagicMock(
            referenced_tweets=[MagicMock(type="quoted")],
            in_reply_to_user_id=None,
            conversation_id="quote_12345",
            id="quote_12345",
        )
        fake_client = MagicMock()
        fake_client.get_users_tweets.return_value.data = [reply, quote]
        fake_client.get_users_tweets.return_value.includes = {}
        fake_client.get_users_tweets.return_value.meta = {"newest_id": "quote_12345"}
        patch_client = self.get_patch_exceptions_x(
            fake_client=fake_client, valid_time_request=False
        )
        self.SocialAccountX.enable_since = True
        reported = set()
        with (
            patch_super,
            patch_client,
            patch.object(
                type(self.SocialAccount),
                "_valid_time_request",
                autospec=True,
                return_value=True,
            ),
            patch_get_statistics,
        ):
            self.SocialAccountX._update_posts_statistics(None, [], reported)
        self.assertFalse(
            self.SocialPostAccount.search(
                [("remote_ref", "in", ["reply_12345", "quote_12345"])]
            ),
            msg="A reply and a quote are not publications of the account.",
        )
        self.assertEqual(
            self.SocialAccountX.last_post_ref,
            "quote_12345",
            msg="The page was read, so the next import starts after it.",
        )
        self.assertEqual(
            reported,
            {self.SocialAccountX.id},
            msg="A page with nothing to store is still a timeline that was read.",
        )

    def test_update_posts_statistics_refused_credentials_flags_the_account(self):
        """X refusing the authorization is not an error to notify and forget.

        The credentials of X cannot be renewed from Odoo, so what the import
        leaves behind is the warning that asks the user to authorize the
        account again.
        """
        patch_super = patch(PATCH_SYNC_ACCOUNT.format("_update_posts_statistics"))
        patch_get_statistics = patch.object(
            type(self.SocialAccount),
            "_get_x_statistics",
            autospec=True,
            return_value=None,
        )
        fake_client = MagicMock()
        fake_client.get_users_tweets.side_effect = Unauthorized(
            self.generate_magic_mock(status_code=401, json_return_value={})
        )
        patch_client = self.get_patch_exceptions_x(
            fake_client=fake_client, valid_time_request=False
        )
        reported = set()
        with (
            patch_super,
            patch_client,
            patch.object(
                type(self.SocialAccount),
                "_valid_time_request",
                autospec=True,
                return_value=True,
            ),
            patch_get_statistics,
        ):
            self.SocialAccountX._update_posts_statistics(None, [], reported)
        self.assertTrue(
            self.SocialAccountX.need_update,
            msg="The dashboard warns about an account X no longer authorizes.",
        )
        self.assertFalse(
            reported, msg="A timeline X refused is not a timeline that was read."
        )

    @mute_logger(LOGGER_ACCOUNT_X_SYNC)
    def test_update_posts_statistics_notifies_any_other_failure(self):
        """Anything else tweepy raises reaches the user as a notification.

        The account is not flagged: what failed says nothing about the
        credentials, and the next pass reads the timeline again.
        """
        patch_super = patch(PATCH_SYNC_ACCOUNT.format("_update_posts_statistics"))
        patch_get_statistics = patch.object(
            type(self.SocialAccount),
            "_get_x_statistics",
            autospec=True,
            return_value=None,
        )
        fake_client = MagicMock()
        fake_client.get_users_tweets.side_effect = Exception("Timeline out of reach")
        patch_client = self.get_patch_exceptions_x(
            fake_client=fake_client, valid_time_request=False
        )
        reported = set()
        with (
            patch_super,
            patch_client,
            patch.object(
                type(self.SocialAccount),
                "_valid_time_request",
                autospec=True,
                return_value=True,
            ),
            patch.object(
                type(self.SocialAccount), "_notify_user_client", autospec=True
            ) as mock_notify,
            patch_get_statistics,
        ):
            self.SocialAccountX._update_posts_statistics(None, [], reported)
        mock_notify.assert_called_once()
        self.assertEqual(
            mock_notify.call_args.kwargs["notif_type"], "social_kanban_danger"
        )
        self.assertEqual(
            mock_notify.call_args.kwargs["notif_message"], "Timeline out of reach"
        )
        self.assertFalse(self.SocialAccountX.need_update)
        self.assertFalse(reported)
