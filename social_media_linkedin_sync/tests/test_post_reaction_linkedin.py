# Copyright 2026 Binhex <https://www.binhex.cloud>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from unittest.mock import patch

from odoo.tests.common import HttpCase, tagged

from odoo.addons.social_media_linkedin.tests.test_common_linkedin import (
    PATCH_ACCOUNT_LINKEDIN,
)

from .test_sync_linkedin_common import (
    PATCH_SYNC_ACCOUNT_LINKEDIN,
    PATCH_SYNC_POST_ACCOUNT_LINKEDIN,
    TestSocialSyncCommonLinkedin,
)

DASHBOARD_URL = "/web#action=social_media_base.social_post_account_action"


@tagged("post_install", "-at_install")
class TestPostReactionLinkedin(HttpCase, TestSocialSyncCommonLinkedin):
    """What pressing the reaction of a card sends to LinkedIn.

    The entry is a toggle, and each half of it has to reach LinkedIn once:
    withdrawing a recommendation that first created one leaves a reaction on
    the publication that nobody asked for.
    """

    def test_reaction_toggle_sends_one_call_each(self):
        publication = self.dashboard_publication(
            self.media_linkedin_id,
            "LinkedIn account of the reaction",
            "LinkedIn reaction publication",
        )
        self.assertFalse(publication.liked_by_account)
        calls = []

        def _react(*args, **kwargs):
            calls.append("like")
            return self.generate_magic_mock(**{"status_code": 201})

        def _unreact(*args, **kwargs):
            calls.append("unlike")
            return self.generate_magic_mock(**{"status_code": 204})

        # The dashboard refreshes itself after every reaction, and neither
        # half of that refresh is what is under test here.
        with patch(
            PATCH_ACCOUNT_LINKEDIN.format("_refresh_statistics"),
            return_value=False,
        ), patch(
            PATCH_SYNC_ACCOUNT_LINKEDIN.format("_update_posts_statistics"),
            return_value=[],
        ), patch(
            PATCH_SYNC_POST_ACCOUNT_LINKEDIN.format("_react_linkedin"),
            side_effect=_react,
        ), patch(
            PATCH_SYNC_POST_ACCOUNT_LINKEDIN.format("_unreact_linkedin"),
            side_effect=_unreact,
        ):
            self.start_tour(
                DASHBOARD_URL,
                "social_media_linkedin_sync.post_reaction",
                login="admin",
            )

        self.assertEqual(calls, ["like", "unlike"])
        self.assertFalse(publication.liked_by_account)
