# Copyright 2026 Binhex <https://www.binhex.cloud>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo.tests.common import HttpCase, tagged

from .test_sync_x_common import TestSocialSyncCommonX

DASHBOARD_URL = "/web#action=social_media_base.social_post_account_action"


@tagged("post_install", "-at_install")
class TestPostReactionX(HttpCase, TestSocialSyncCommonX):
    """What pressing the like of a card of X sends to X.

    The entry is a toggle, and each half of it reaches X once.
    """

    def test_reaction_toggle_sends_one_call_each(self):
        publication = self.dashboard_publication(
            self.media_x_id, "X account of the reaction", "X reaction publication"
        )
        self.assertFalse(publication.liked_by_account)
        calls = []

        def x_react(post_account, tweet_ref, like):
            calls.append((tweet_ref, like))
            return like

        SocialAccount = type(self.SocialAccount)
        # The dashboard refreshes itself after every reaction, and neither
        # half of that refresh is what is under test here.
        self.patch(SocialAccount, "_refresh_statistics", lambda self: False)
        self.patch(
            SocialAccount,
            "_update_posts_statistics",
            lambda self, post_id, domain, imported=None: [],
        )
        self.patch(type(self.SocialPostAccount), "_x_react", x_react)
        self.start_tour(
            DASHBOARD_URL, "social_media_x_sync.post_reaction", login="admin"
        )
        self.assertEqual(
            calls,
            [(publication.remote_ref, True), (publication.remote_ref, False)],
        )
        self.assertFalse(publication.liked_by_account)
