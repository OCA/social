# Copyright 2026 Binhex <https://www.binhex.cloud>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import json
from unittest.mock import MagicMock, patch

import psycopg2
from psycopg2 import errorcodes

from odoo import _
from odoo.exceptions import UserError
from odoo.tests.common import tagged
from odoo.tools import mute_logger

from odoo.addons.social_media_base.tests.test_social_common import (
    PATCH_SOCIAL_BASE_MIXIN,
)

from ..exceptions import LinkedinRequestRejectedError
from ..social_linkedin_utils import _QUERY_STRING_MAX_BYTES_LINKEDIN
from .test_common_linkedin import (
    PATCH_ACCOUNT_LINKEDIN,
    PATCH_POST_ACCOUNT_LINKEDIN,
    TestSocialCommonLinkedin,
)

LOGGER_ACCOUNT_LINKEDIN = "odoo.addons.social_media_linkedin.models.social_account"
LOGGER_ACCOUNT_BASE = "odoo.addons.social_media_base.models.social_account"
REJECTION_LINKEDIN = (
    "Unable to get activityIds from any of the given shares. Either the "
    "shares/ugcPosts do not have corresponding activities or the "
    "organizational entity did not post them."
)


@tagged("post_install", "-at_install")
class TestLinkedinPostStatistics(TestSocialCommonLinkedin):
    """The figures LinkedIn reports for a publication, read by URN.

    Three calls answer a whole page of publications, which is what lets the
    connector read them without importing anything: Odoo already knows the
    URNs of what it published.
    """

    def test_get_entity_statistics_does_not_mutate_params(self):
        params_fields = ["q", "organizationalEntity"]
        params_values = {
            "q": "organizationalEntity",
            "organizationalEntity": "urn:li:organization:123456",
        }
        with patch(
            PATCH_ACCOUNT_LINKEDIN.format("_get_entity_share_statistics"),
            autospec=True,
            return_value={},
        ), patch(
            PATCH_ACCOUNT_LINKEDIN.format("_get_ugc_posts_statistics"),
            autospec=True,
            return_value={},
        ):
            self.SocialAccountLinkedin._get_entity_statistics(
                posts=[{"id": "urn:li:ugcPost:1"}],
                params_fields=params_fields,
                params_values=params_values,
            )
        self.assertEqual(params_fields, ["q", "organizationalEntity"])
        self.assertEqual(
            params_values,
            {
                "q": "organizationalEntity",
                "organizationalEntity": "urn:li:organization:123456",
            },
        )

    def test_get_entity_share_statistics_of_the_shares(self):
        params_fields = ["q"]
        params_values = {"q": "organizationalEntity"}
        self.assertEqual(
            self.SocialAccountLinkedin._get_entity_share_statistics(
                [],
                "shares",
                "share",
                "boom",
                params_fields=params_fields,
                params_values=params_values,
            ),
            {},
            msg="Nothing of this kind in the feed, nothing to ask for.",
        )
        self.assertNotIn("shares", params_fields)
        response = MagicMock(status_code=200)
        response.json.return_value = {
            "elements": [
                {
                    "share": "urn:li:share:1",
                    "totalShareStatistics": {
                        "clickCount": 1,
                        "likeCount": 2,
                        "commentCount": 3,
                        "shareCount": 4,
                        "engagement": 0.5,
                        "impressionCount": 6,
                    },
                }
            ]
        }
        with patch(
            PATCH_ACCOUNT_LINKEDIN.format("_request_linkedin"),
            autospec=True,
            return_value=response,
        ) as mock_request:
            data = self.SocialAccountLinkedin._get_entity_share_statistics(
                ["urn:li:share:1"],
                "shares",
                "share",
                "boom",
                params_fields=params_fields,
                params_values=params_values,
            )
        self.assertEqual(data, {"urn:li:share:1": (1, 2, 3, 4, 0.5, 6)})
        self.assertEqual(
            (params_fields, params_values),
            (["q"], {"q": "organizationalEntity"}),
            msg="The parameters of the caller are left alone.",
        )
        self.assertEqual(
            mock_request.call_args.kwargs["params_values"]["shares"],
            ["urn:li:share:1"],
        )
        self.assertEqual(
            mock_request.call_args.kwargs["endpoint"],
            "/organizationalEntityShareStatistics",
        )
        error_response = MagicMock(status_code=400)
        error_response.json.return_value = {"message": "Invalid share urn"}
        with patch(
            PATCH_ACCOUNT_LINKEDIN.format("_request_linkedin"),
            autospec=True,
            return_value=error_response,
        ):
            with self.assertRaises(UserError):
                self.SocialAccountLinkedin._get_entity_share_statistics(
                    ["urn:li:share:1"],
                    "shares",
                    "share",
                    "boom",
                    params_fields=["q"],
                    params_values={"q": "organizationalEntity"},
                )

    def test_get_ugc_posts_statistics(self):
        self.assertEqual(self.SocialAccountLinkedin._get_ugc_posts_statistics(), {})
        params_fields = ["q"]
        params_values = {"q": "organizationalEntity"}
        self.assertEqual(
            self.SocialAccountLinkedin._get_ugc_posts_statistics(
                posts=[{"id": "urn:li:share:1"}],
                params_fields=params_fields,
                params_values=params_values,
            ),
            {},
            msg="The UGC posts endpoint ignores the shares.",
        )
        self.assertNotIn("ids", params_fields)
        response = MagicMock(status_code=200)
        response.json.return_value = {
            "results": {
                "urn:li:ugcPost:1": {
                    "likesSummary": {"totalLikes": 7},
                    "commentsSummary": {"aggregatedTotalComments": 8},
                }
            }
        }
        with patch(
            PATCH_ACCOUNT_LINKEDIN.format("_request_linkedin"),
            autospec=True,
            return_value=response,
        ) as mock_request:
            data = self.SocialAccountLinkedin._get_ugc_posts_statistics(
                posts=[{"id": "urn:li:ugcPost:1"}, {"id": "urn:li:share:2"}],
                params_fields=params_fields,
                params_values=params_values,
            )
        self.assertEqual(
            data,
            {"urn:li:ugcPost:1": (7, 8)},
            msg="socialActions only knows the likes and the comments.",
        )
        self.assertEqual(
            (params_fields, params_values),
            (["q"], {"q": "organizationalEntity"}),
            msg="The parameters of the caller are left alone.",
        )
        self.assertEqual(
            mock_request.call_args.kwargs["params_values"]["ids"],
            ["urn:li:ugcPost:1"],
        )
        self.assertEqual(mock_request.call_args.kwargs["endpoint"], "/socialActions")
        error_response = MagicMock(status_code=400)
        error_response.json.return_value = {"message": "Invalid ugc post urn"}
        with patch(
            PATCH_ACCOUNT_LINKEDIN.format("_request_linkedin"),
            autospec=True,
            return_value=error_response,
        ):
            with self.assertRaises(UserError):
                self.SocialAccountLinkedin._get_ugc_posts_statistics(
                    posts=[{"id": "urn:li:ugcPost:1"}],
                    params_fields=["q"],
                    params_values={"q": "organizationalEntity"},
                )

    def test_get_entity_share_statistics_splits_the_urns(self):
        """A feed of more than a page fits in no single query string."""
        urns = self._fake_urns("urn:li:share:", 250)
        response = MagicMock(status_code=200)
        response.json.return_value = {"elements": []}
        with patch(
            PATCH_ACCOUNT_LINKEDIN.format("_request_linkedin"),
            autospec=True,
            return_value=response,
        ) as mock_request:
            self.SocialAccountLinkedin._get_entity_share_statistics(
                urns,
                "shares",
                "share",
                "boom",
                params_fields=["q", "organizationalEntity"],
                params_values={
                    "q": "organizationalEntity",
                    "organizationalEntity": "urn:li:organization:123456",
                },
            )
        self.assertGreater(mock_request.call_count, 1)
        asked = []
        for call in mock_request.call_args_list:
            self.assertLess(
                len(self._linkedin_query_string(call).encode()),
                _QUERY_STRING_MAX_BYTES_LINKEDIN,
            )
            asked.extend(call.kwargs["params_values"]["shares"][0].split(","))
        self.assertEqual(asked, urns, msg="Every URN is asked for exactly once.")

    def test_get_ugc_posts_statistics_splits_the_urns(self):
        urns = self._fake_urns("urn:li:ugcPost:", 250)
        response = MagicMock(status_code=200)
        response.json.return_value = {"results": {}}
        with patch(
            PATCH_ACCOUNT_LINKEDIN.format("_request_linkedin"),
            autospec=True,
            return_value=response,
        ) as mock_request:
            self.SocialAccountLinkedin._get_ugc_posts_statistics(
                posts=[{"id": urn} for urn in urns],
                params_fields=[],
                params_values={},
            )
        self.assertGreater(mock_request.call_count, 1)
        asked = []
        for call in mock_request.call_args_list:
            self.assertLess(
                len(self._linkedin_query_string(call).encode()),
                _QUERY_STRING_MAX_BYTES_LINKEDIN,
            )
            asked.extend(call.kwargs["params_values"]["ids"][0].split(","))
        self.assertEqual(asked, urns)

    def test_get_entity_share_statistics_of_the_ugc_posts(self):
        """The UGC posts answer the same block of figures as the shares."""
        response = MagicMock(status_code=200)
        response.json.return_value = {
            "elements": [
                {
                    "ugcPost": "urn:li:ugcPost:1",
                    "totalShareStatistics": {
                        "clickCount": 9,
                        "likeCount": 1,
                        "commentCount": 2,
                        "shareCount": 3,
                        "engagement": 0.25,
                        "impressionCount": 40,
                    },
                },
                {"organizationalEntity": "urn:li:organization:123456"},
            ]
        }
        with patch(
            PATCH_ACCOUNT_LINKEDIN.format("_request_linkedin"),
            autospec=True,
            return_value=response,
        ) as mock_request:
            data = self.SocialAccountLinkedin._get_entity_share_statistics(
                ["urn:li:ugcPost:1"],
                "ugcPosts",
                "ugcPost",
                "boom",
                params_fields=["q"],
                params_values={"q": "organizationalEntity"},
            )
        self.assertEqual(
            data,
            {"urn:li:ugcPost:1": (9, 1, 2, 3, 0.25, 40)},
            msg="The aggregate element, which names no entity, is left out.",
        )
        self.assertEqual(
            mock_request.call_args.kwargs["params_values"]["ugcPosts"],
            ["urn:li:ugcPost:1"],
        )
        self.assertEqual(
            mock_request.call_args.kwargs["endpoint"],
            "/organizationalEntityShareStatistics",
        )
        error_response = MagicMock(status_code=400)
        error_response.json.return_value = {"message": "Invalid ugc post urn"}
        with patch(
            PATCH_ACCOUNT_LINKEDIN.format("_request_linkedin"),
            autospec=True,
            return_value=error_response,
        ):
            with self.assertRaises(UserError):
                self.SocialAccountLinkedin._get_entity_share_statistics(
                    ["urn:li:ugcPost:1"],
                    "ugcPosts",
                    "ugcPost",
                    "boom",
                    params_fields=["q"],
                    params_values={"q": "organizationalEntity"},
                )

    def _refused_response(self, status_code, message):
        return MagicMock(status_code=status_code, text=json.dumps({"message": message}))

    def test_get_entity_share_statistics_rejected_with_a_4xx(self):
        """A 4xx is LinkedIn refusing the request, told apart for the caller."""
        with patch(
            PATCH_ACCOUNT_LINKEDIN.format("_request_linkedin"),
            autospec=True,
            return_value=self._refused_response(400, "Invalid share urn"),
        ):
            with self.assertRaises(LinkedinRequestRejectedError) as error:
                self.SocialAccountLinkedin._get_entity_share_statistics(
                    ["urn:li:share:1"],
                    "shares",
                    "share",
                    "boom",
                    params_fields=["q"],
                    params_values={"q": "organizationalEntity"},
                )
        self.assertIsInstance(error.exception, UserError)
        self.assertEqual(error.exception.status_code, 400)
        self.assertEqual(error.exception.args[0], "boom: Invalid share urn")

    def test_get_entity_share_statistics_failing_with_a_5xx(self):
        """Any other status says nothing about the publications asked for."""
        with patch(
            PATCH_ACCOUNT_LINKEDIN.format("_request_linkedin"),
            autospec=True,
            return_value=self._refused_response(500, "Internal error"),
        ):
            with self.assertRaises(UserError) as error:
                self.SocialAccountLinkedin._get_entity_share_statistics(
                    ["urn:li:share:1"],
                    "shares",
                    "share",
                    "boom",
                    params_fields=["q"],
                    params_values={"q": "organizationalEntity"},
                )
        self.assertNotIsInstance(error.exception, LinkedinRequestRejectedError)
        self.assertEqual(error.exception.args[0], "boom: Internal error")

    def test_get_ugc_posts_statistics_rejected_with_a_4xx(self):
        with patch(
            PATCH_ACCOUNT_LINKEDIN.format("_request_linkedin"),
            autospec=True,
            return_value=self._refused_response(400, "Invalid ugc post urn"),
        ):
            with self.assertRaises(LinkedinRequestRejectedError) as error:
                self.SocialAccountLinkedin._get_ugc_posts_statistics(
                    posts=[{"id": "urn:li:ugcPost:1"}],
                    params_fields=[],
                    params_values={},
                )
        self.assertIsInstance(error.exception, UserError)
        self.assertEqual(error.exception.status_code, 400)
        self.assertEqual(
            error.exception.args[0],
            "The likes and the comments of the publications could not be read: "
            "Invalid ugc post urn",
        )

    def test_get_ugc_posts_statistics_failing_with_a_5xx(self):
        with patch(
            PATCH_ACCOUNT_LINKEDIN.format("_request_linkedin"),
            autospec=True,
            return_value=self._refused_response(503, "Service unavailable"),
        ):
            with self.assertRaises(UserError) as error:
                self.SocialAccountLinkedin._get_ugc_posts_statistics(
                    posts=[{"id": "urn:li:ugcPost:1"}],
                    params_fields=[],
                    params_values={},
                )
        self.assertNotIsInstance(error.exception, LinkedinRequestRejectedError)

    def test_get_entity_statistics_merges_the_two_ugc_sources(self):
        """A UGC post keeps its figures and takes its likes from the feed."""
        entity_answers = {
            "shares": {"urn:li:share:1": (1, 2, 3, 4, 0.5, 6)},
            "ugcPosts": {"urn:li:ugcPost:1": (9, 0, 0, 3, 0.25, 40)},
        }
        with patch(
            PATCH_ACCOUNT_LINKEDIN.format("_get_entity_share_statistics"),
            autospec=True,
            side_effect=lambda account, urns, param_field, *args, **kwargs: (
                entity_answers[param_field]
            ),
        ), patch(
            PATCH_ACCOUNT_LINKEDIN.format("_get_ugc_posts_statistics"),
            autospec=True,
            return_value={"urn:li:ugcPost:1": (7, 8), "urn:li:ugcPost:2": (1, 2)},
        ) as mock_social_actions:
            data = self.SocialAccountLinkedin._get_entity_statistics(
                posts=[{"id": "urn:li:share:1"}, {"id": "urn:li:ugcPost:1"}]
            )
        self.assertEqual(
            data,
            {
                "urn:li:share:1": (1, 2, 3, 4, 0.5, 6),
                "urn:li:ugcPost:1": (9, 7, 8, 3, 0.25, 40),
                "urn:li:ugcPost:2": (0, 1, 2, 0, 0, 0),
            },
        )
        self.assertEqual(
            mock_social_actions.call_args.kwargs["params_fields"],
            [],
            msg="socialActions takes neither the finder nor the organization.",
        )
        self.assertEqual(mock_social_actions.call_args.kwargs["params_values"], {})

    def _linkedin_publication(self, urn, account=None, **values):
        """Create a publication of a LinkedIn account, online and referenced."""
        return self.SocialPostAccount.create(
            dict(
                {
                    "message": "Test Message",
                    "account_id": (account or self.SocialAccountLinkedin).id,
                    "post_id": self.SocialPostLinkedin.id,
                    "remote_ref": urn,
                    "state": "posted",
                },
                **values,
            )
        )

    def test_refresh_post_statistics_writes_what_linkedin_answered(self):
        """The figures of the answer land on the line, with the date read."""
        line = self._linkedin_publication("urn:li:share:1")
        with patch(
            PATCH_ACCOUNT_LINKEDIN.format("_get_entity_statistics"),
            autospec=True,
            return_value={"urn:li:share:1": (3, 5, 7, 9, 0.5, 100)},
        ):
            refreshed = self.SocialAccountLinkedin._refresh_post_statistics(line)
        self.assertEqual(refreshed, line)
        self.assertEqual(line.click_count, 3)
        self.assertEqual(line.like_count, 5)
        self.assertEqual(line.comment_count, 7)
        self.assertEqual(line.share_count, 9)
        self.assertEqual(line.engagement, 0.5)
        self.assertEqual(line.impression_count, 100)
        self.assertTrue(line.statistics_date)

    def test_refresh_post_statistics_spends_three_calls(self):
        """A whole page of publications costs three calls.

        Two of ``organizationalEntityShareStatistics``, one per kind of
        publication, and one of ``socialActions`` for the likes and the
        comments of the UGC posts. Nothing walks the feed: Odoo already knows
        the URNs, so the page is answered whatever the account has published.
        """
        urns = self._fake_urns("urn:li:share:", 25) + self._fake_urns(
            "urn:li:ugcPost:", 25
        )
        lines = self.SocialPostAccount.union(
            *[self._linkedin_publication(urn) for urn in urns]
        )
        answered = MagicMock()
        answered.status_code = 200
        answered.json.return_value = {"elements": [], "results": {}}
        with patch(
            PATCH_ACCOUNT_LINKEDIN.format("_request_linkedin"),
            autospec=True,
            return_value=answered,
        ) as mock_request:
            self.SocialAccountLinkedin._refresh_post_statistics(lines)
        self.assertEqual(mock_request.call_count, 3)

    def test_a_page_longer_than_the_query_string_is_split(self):
        """What decides the calls is the query string, not the publications.

        The URNs travel in the query string of a finder LinkedIn documents as
        not paginated, so a page whose URNs do not fit in
        ``_QUERY_STRING_MAX_BYTES_LINKEDIN`` is asked for in as many calls as
        it takes. It is the only thing that adds a call to the three.
        """
        urns = self._fake_urns("urn:li:ugcPost:", 200)
        lines = self.SocialPostAccount.union(
            *[self._linkedin_publication(urn) for urn in urns]
        )
        answered = MagicMock()
        answered.status_code = 200
        answered.json.return_value = {"elements": [], "results": {}}
        with patch(
            PATCH_ACCOUNT_LINKEDIN.format("_request_linkedin"),
            autospec=True,
            return_value=answered,
        ) as mock_request:
            self.SocialAccountLinkedin._refresh_post_statistics(lines)
        for call in mock_request.call_args_list:
            self.assertLess(
                len(self._linkedin_query_string(call).encode()),
                _QUERY_STRING_MAX_BYTES_LINKEDIN,
            )
        # No call of the shares: none of these URNs is one.
        self.assertGreater(mock_request.call_count, 3)

    def test_a_publication_linkedin_left_out_stays_at_zero(self):
        """Silence about a URN is a figure of zero, not a reading that failed.

        ``organizationalEntityShareStatistics`` leaves out the entities with no
        activity at all, so the publication nobody interacted with is the one
        missing from the answer.
        """
        quiet = self._linkedin_publication("urn:li:share:1", like_count=4)
        busy = self._linkedin_publication("urn:li:share:2")
        with patch(
            PATCH_ACCOUNT_LINKEDIN.format("_get_entity_statistics"),
            autospec=True,
            return_value={"urn:li:share:2": (0, 8, 0, 0, 0, 0)},
        ):
            refreshed = self.SocialAccountLinkedin._refresh_post_statistics(
                quiet + busy
            )
        self.assertEqual(refreshed, quiet + busy)
        self.assertEqual(quiet.like_count, 0)
        self.assertEqual(busy.like_count, 8)
        self.assertTrue(quiet.statistics_date)

    def test_refresh_post_statistics_leaves_another_media_alone(self):
        """A line of another social media is handed to the next connector."""
        linkedin = self._linkedin_publication("urn:li:share:1")
        other = self.social_post_account_id
        with patch(
            PATCH_ACCOUNT_LINKEDIN.format("_get_entity_statistics"),
            autospec=True,
            return_value={},
        ) as mock_statistics:
            refreshed = self.SocialAccountLinkedin._refresh_post_statistics(
                linkedin + other
            )
        self.assertEqual(refreshed, linkedin)
        self.assertNotIn(other, refreshed)
        self.assertEqual(
            [{"id": "urn:li:share:1"}], mock_statistics.call_args.kwargs["posts"]
        )
        self.assertFalse(other.statistics_date)

    def test_an_account_without_an_organization_is_not_asked(self):
        """The finder is addressed by organization, so there is nothing to ask."""
        self.SocialAccountLinkedin.remote_ref = False
        line = self._linkedin_publication("urn:li:share:1")
        with patch(
            PATCH_ACCOUNT_LINKEDIN.format("_get_entity_statistics"), autospec=True
        ) as mock_statistics:
            refreshed = self.SocialAccountLinkedin._refresh_post_statistics(line)
        mock_statistics.assert_not_called()
        self.assertFalse(refreshed)

    @mute_logger(LOGGER_ACCOUNT_LINKEDIN)
    def test_an_account_linkedin_refuses_does_not_stop_the_next(self):
        """Each account is read in its own savepoint and its user is told."""
        refused = self._linkedin_publication("urn:li:share:1")
        answered = self._linkedin_publication(
            "urn:li:share:2", account=self.SocialAccountLinkedinData
        )

        def statistics(account, posts=None, **kwargs):
            if account == self.SocialAccountLinkedin:
                raise UserError(_("LinkedIn refused the statistics"))
            return {"urn:li:share:2": (0, 2, 0, 0, 0, 0)}

        with patch(
            PATCH_ACCOUNT_LINKEDIN.format("_get_entity_statistics"),
            autospec=True,
            side_effect=statistics,
        ):
            accounts = self.SocialAccountLinkedin + self.SocialAccountLinkedinData
            refreshed = accounts._refresh_post_statistics(refused + answered)
        self.assertEqual(refreshed, answered)
        self.assertFalse(refused.statistics_date)
        self.assertEqual(answered.like_count, 2)

    def _refuse_first_batches(self, refusals, answer):
        """Refuse the first batches of figures and answer the next ones.

        :param refusals: how many batches in a row LinkedIn refuses.
        :param answer: what it answers once it stops refusing.
        :return: the URNs of every batch asked for, and the side effect.
        """
        batches = []

        def statistics(account, posts=None, **kwargs):
            batches.append([post["id"] for post in posts])
            if len(batches) <= refusals:
                raise LinkedinRequestRejectedError(_(REJECTION_LINKEDIN), 400)
            return answer

        return batches, statistics

    def _patch_posts_gone(self, gone_urns):
        return patch(
            PATCH_ACCOUNT_LINKEDIN.format("_get_posts_gone"),
            autospec=True,
            side_effect=lambda account, urns: set(gone_urns) & set(urns),
        )

    def _patch_notify_user(self):
        return patch(PATCH_SOCIAL_BASE_MIXIN.format("_notify_user"), autospec=True)

    def _danger_notifications(self, mock_notify):
        return [
            call.kwargs["notif_message"]
            for call in mock_notify.call_args_list
            if call.kwargs.get("notif_type") == "social_kanban_danger"
        ]

    def test_a_refused_batch_marks_the_deleted_and_reads_the_rest(self):
        """A publication deleted on LinkedIn no longer costs the others."""
        gone = self._linkedin_publication("urn:li:share:1")
        alive = self._linkedin_publication("urn:li:share:2")
        batches, statistics = self._refuse_first_batches(
            1, {"urn:li:share:2": (1, 6, 0, 0, 0.5, 30)}
        )
        with patch(
            PATCH_ACCOUNT_LINKEDIN.format("_get_entity_statistics"),
            autospec=True,
            side_effect=statistics,
        ), self._patch_posts_gone(
            ["urn:li:share:1"]
        ) as mock_gone, self._patch_notify_user() as mock_notify, self.assertLogs(
            LOGGER_ACCOUNT_LINKEDIN, "INFO"
        ) as logs:
            refreshed = self.SocialAccountLinkedin._refresh_post_statistics(
                gone + alive
            )
        self.assertEqual(gone.state, "deleted")
        self.assertFalse(gone.statistics_date)
        self.assertEqual(alive.state, "posted")
        self.assertEqual(alive.like_count, 6)
        self.assertEqual(alive.impression_count, 30)
        self.assertTrue(alive.statistics_date)
        self.assertEqual(
            batches,
            [["urn:li:share:1", "urn:li:share:2"], ["urn:li:share:2"]],
            msg="The second batch only asks for the publication still online.",
        )
        mock_gone.assert_called_once()
        self.assertFalse(self._danger_notifications(mock_notify))
        self.assertEqual(refreshed, alive)
        info = [line for line in logs.output if line.startswith("INFO:")]
        self.assertEqual(len(info), 1)
        self.assertIn(self.SocialAccountLinkedin.name, info[0])
        self.assertIn(" 1 of its publications", info[0])
        self.assertIn(REJECTION_LINKEDIN, info[0])

    @mute_logger(LOGGER_ACCOUNT_LINKEDIN, LOGGER_ACCOUNT_BASE)
    def test_a_refused_batch_with_nothing_confirmed_fails_as_before(self):
        """No publication explains the refusal, so it is told as it is."""
        first = self._linkedin_publication("urn:li:share:1", like_count=4)
        second = self._linkedin_publication("urn:li:share:2")
        batches, statistics = self._refuse_first_batches(1, {})
        with patch(
            PATCH_ACCOUNT_LINKEDIN.format("_get_entity_statistics"),
            autospec=True,
            side_effect=statistics,
        ), self._patch_posts_gone([]), self._patch_notify_user() as mock_notify:
            refreshed = self.SocialAccountLinkedin._refresh_post_statistics(
                first + second
            )
        self.assertEqual((first + second).mapped("state"), ["posted", "posted"])
        self.assertFalse((first + second).filtered("statistics_date"))
        self.assertEqual(first.like_count, 4)
        self.assertEqual(len(batches), 1, msg="Nothing confirmed, nothing retried.")
        notified = self._danger_notifications(mock_notify)
        self.assertEqual(len(notified), 1)
        self.assertIn(REJECTION_LINKEDIN, notified[0])
        self.assertFalse(refreshed)

    @mute_logger(LOGGER_ACCOUNT_LINKEDIN, LOGGER_ACCOUNT_BASE)
    def test_a_second_refusal_keeps_the_deleted_marked(self):
        """The marks live in their own savepoint and there is no third try."""
        gone = self._linkedin_publication("urn:li:share:1")
        alive = self._linkedin_publication("urn:li:share:2")
        batches, statistics = self._refuse_first_batches(
            2, {"urn:li:share:2": (0, 6, 0, 0, 0, 0)}
        )
        with patch(
            PATCH_ACCOUNT_LINKEDIN.format("_get_entity_statistics"),
            autospec=True,
            side_effect=statistics,
        ), self._patch_posts_gone(
            ["urn:li:share:1"]
        ), self._patch_notify_user() as mock_notify:
            refreshed = self.SocialAccountLinkedin._refresh_post_statistics(
                gone + alive
            )
        self.assertEqual(gone.state, "deleted")
        self.assertFalse(alive.statistics_date)
        self.assertEqual(alive.like_count, 0)
        self.assertEqual(len(batches), 2)
        self.assertEqual(len(self._danger_notifications(mock_notify)), 1)
        self.assertFalse(refreshed)

    def test_a_refused_batch_all_deleted_is_not_retried(self):
        """Nothing left to read, nothing to ask for and nobody to tell."""
        lines = self._linkedin_publication(
            "urn:li:share:1"
        ) + self._linkedin_publication("urn:li:share:2")
        batches, statistics = self._refuse_first_batches(1, {})
        with patch(
            PATCH_ACCOUNT_LINKEDIN.format("_get_entity_statistics"),
            autospec=True,
            side_effect=statistics,
        ), self._patch_posts_gone(
            ["urn:li:share:1", "urn:li:share:2"]
        ), self._patch_notify_user() as mock_notify, mute_logger(
            LOGGER_ACCOUNT_LINKEDIN
        ):
            refreshed = self.SocialAccountLinkedin._refresh_post_statistics(lines)
        self.assertEqual(lines.mapped("state"), ["deleted", "deleted"])
        self.assertEqual(len(batches), 1)
        self.assertFalse(self._danger_notifications(mock_notify))
        self.assertFalse(refreshed)

    @mute_logger(LOGGER_ACCOUNT_LINKEDIN, LOGGER_ACCOUNT_BASE)
    def test_a_failure_other_than_a_4xx_is_not_looked_into(self):
        """A 5xx says nothing about the publications, so none is asked about."""
        line = self._linkedin_publication("urn:li:share:1")
        with patch(
            PATCH_ACCOUNT_LINKEDIN.format("_get_entity_statistics"),
            autospec=True,
            side_effect=UserError(_("Internal error")),
        ), self._patch_posts_gone(
            ["urn:li:share:1"]
        ) as mock_gone, self._patch_notify_user() as mock_notify:
            refreshed = self.SocialAccountLinkedin._refresh_post_statistics(line)
        mock_gone.assert_not_called()
        self.assertEqual(line.state, "posted")
        self.assertEqual(len(self._danger_notifications(mock_notify)), 1)
        self.assertFalse(refreshed)

    def test_a_check_that_fails_confirms_nothing(self):
        """The error of the check goes to the log, the refusal to the user."""
        self.SocialAccountLinkedin.linkedin_granted_scopes = "w_organization_social"
        first = self._linkedin_publication("urn:li:share:1")
        second = self._linkedin_publication("urn:li:share:2")
        batches, statistics = self._refuse_first_batches(1, {})
        with patch(
            PATCH_ACCOUNT_LINKEDIN.format("_get_entity_statistics"),
            autospec=True,
            side_effect=statistics,
        ), self._patch_posts_gone(
            ["urn:li:share:1"]
        ) as mock_gone, self._patch_notify_user() as mock_notify, self.assertLogs(
            LOGGER_ACCOUNT_LINKEDIN, "ERROR"
        ) as logs:
            refreshed = self.SocialAccountLinkedin._refresh_post_statistics(
                first + second
            )
        mock_gone.assert_not_called()
        self.assertEqual((first + second).mapped("state"), ["posted", "posted"])
        self.assertFalse((first + second).filtered("statistics_date"))
        self.assertEqual(len(batches), 1)
        self.assertTrue(
            any("Error checking which publications" in line for line in logs.output)
        )
        notified = self._danger_notifications(mock_notify)
        self.assertEqual(len(notified), 1)
        self.assertIn(REJECTION_LINKEDIN, notified[0])
        self.assertNotIn("r_organization_social", notified[0])
        self.assertFalse(refreshed)

    def test_a_concurrent_update_during_the_check_confirms_nothing(self):
        """Not even the concurrency error of the check escapes the refusal."""

        class ConcurrencyError(psycopg2.OperationalError):
            pgcode = errorcodes.SERIALIZATION_FAILURE

        first = self._linkedin_publication("urn:li:share:1")
        second = self._linkedin_publication("urn:li:share:2")
        batches, statistics = self._refuse_first_batches(1, {})
        with patch(
            PATCH_ACCOUNT_LINKEDIN.format("_get_entity_statistics"),
            autospec=True,
            side_effect=statistics,
        ), patch(
            PATCH_POST_ACCOUNT_LINKEDIN.format("_check_remote_posts_exist"),
            autospec=True,
            side_effect=ConcurrencyError("serialization conflict"),
        ), self._patch_notify_user() as mock_notify, self.assertLogs(
            LOGGER_ACCOUNT_LINKEDIN, "ERROR"
        ) as logs:
            refreshed = self.SocialAccountLinkedin._refresh_post_statistics(
                first + second
            )
        self.assertEqual((first + second).mapped("state"), ["posted", "posted"])
        self.assertEqual(len(batches), 1)
        self.assertTrue(
            any("Error checking which publications" in line for line in logs.output)
        )
        notified = self._danger_notifications(mock_notify)
        self.assertEqual(len(notified), 1)
        self.assertIn(REJECTION_LINKEDIN, notified[0])
        self.assertFalse(refreshed)

    def test_a_refusal_of_social_actions_is_recovered_the_same(self):
        """The 4xx of ``socialActions`` on a UGC post is looked into as well."""
        gone = self._linkedin_publication("urn:li:ugcPost:1")
        alive = self._linkedin_publication("urn:li:ugcPost:2")
        asked = []

        def request(account, endpoint=None, params_values=None, **kwargs):
            if endpoint != "/socialActions":
                response = MagicMock(status_code=200)
                response.json.return_value = {"elements": []}
                return response
            asked.append(params_values["ids"][0].split(","))
            if len(asked) == 1:
                return self._refused_response(400, REJECTION_LINKEDIN)
            response = MagicMock(status_code=200)
            response.json.return_value = {
                "results": {
                    "urn:li:ugcPost:2": {
                        "likesSummary": {"totalLikes": 3},
                        "commentsSummary": {"aggregatedTotalComments": 2},
                    }
                }
            }
            return response

        with patch(
            PATCH_ACCOUNT_LINKEDIN.format("_request_linkedin"),
            autospec=True,
            side_effect=request,
        ), self._patch_posts_gone(
            ["urn:li:ugcPost:1"]
        ), self._patch_notify_user() as mock_notify, mute_logger(
            LOGGER_ACCOUNT_LINKEDIN
        ):
            refreshed = self.SocialAccountLinkedin._refresh_post_statistics(
                gone + alive
            )
        self.assertEqual(gone.state, "deleted")
        self.assertEqual(alive.like_count, 3)
        self.assertEqual(alive.comment_count, 2)
        self.assertTrue(alive.statistics_date)
        self.assertEqual(
            asked, [["urn:li:ugcPost:1", "urn:li:ugcPost:2"], ["urn:li:ugcPost:2"]]
        )
        self.assertFalse(self._danger_notifications(mock_notify))
        self.assertEqual(refreshed, alive)

    def test_the_recovery_of_an_account_leaves_the_next_alone(self):
        """The other account writes its figures with a single reading."""
        gone = self._linkedin_publication("urn:li:share:1")
        alive = self._linkedin_publication("urn:li:share:2")
        other = self._linkedin_publication(
            "urn:li:share:3", account=self.SocialAccountLinkedinData
        )
        batches = {}

        def statistics(account, posts=None, **kwargs):
            asked = batches.setdefault(account, [])
            asked.append([post["id"] for post in posts])
            if account == self.SocialAccountLinkedin and len(asked) == 1:
                raise LinkedinRequestRejectedError(_(REJECTION_LINKEDIN), 400)
            return {
                "urn:li:share:2": (0, 6, 0, 0, 0, 0),
                "urn:li:share:3": (0, 9, 0, 0, 0, 0),
            }

        accounts = self.SocialAccountLinkedin + self.SocialAccountLinkedinData
        with patch(
            PATCH_ACCOUNT_LINKEDIN.format("_get_entity_statistics"),
            autospec=True,
            side_effect=statistics,
        ), self._patch_posts_gone(
            ["urn:li:share:1"]
        ), self._patch_notify_user() as mock_notify, mute_logger(
            LOGGER_ACCOUNT_LINKEDIN
        ):
            refreshed = accounts._refresh_post_statistics(gone + alive + other)
        self.assertEqual(gone.state, "deleted")
        self.assertEqual(alive.like_count, 6)
        self.assertEqual(other.like_count, 9)
        self.assertTrue(other.statistics_date)
        self.assertEqual(batches[self.SocialAccountLinkedinData], [["urn:li:share:3"]])
        self.assertFalse(self._danger_notifications(mock_notify))
        self.assertEqual(refreshed, alive + other)
