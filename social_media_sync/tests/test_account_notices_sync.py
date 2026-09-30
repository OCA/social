# Copyright 2026 Binhex <https://www.binhex.cloud>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo.tests.common import HttpCase, tagged

from .test_social_sync_common import TestSocialMediaSyncCommon

DASHBOARD_URL = "/web#action=social_media_base.social_post_account_action"


@tagged("post_install", "-at_install")
class TestAccountNoticesSync(HttpCase, TestSocialMediaSyncCommon):
    """What the dashboard says about what is pending on an account.

    On the cards, where expired credentials and publications left to import
    are independent — one asks the user for a new authorization and the other
    for an import, so an account can be carrying either, both or neither and
    the card has to say exactly that. And on the *Update* button, which has to
    tell a run that imported something from one that had nothing to import.
    """

    def _account_of_the_notices(self, **flags):
        """Leave a single account with flags in front of the tour.

        The dashboard draws every account its user may read, so the flags of
        the ones already stored are taken down first: what the tour asserts
        must not depend on the database it happens to run against.
        """
        user = self.env.ref("base.user_admin")
        user.sudo().write(
            {
                "groups_id": [
                    (
                        4,
                        self.env.ref("social_media_base.group_social_media_manager").id,
                    )
                ]
            }
        )
        self.SocialAccount.sudo().search([]).write(
            {
                "need_update": False,
                "posts_need_import": False,
                "pending_initial_sync": False,
            }
        )
        media = self.SocialMedia.create({"name": "Notices"})
        return self.SocialAccount.create(
            {
                "name": "Notices account",
                "media_id": media.id,
                "user_id": user.id,
                **flags,
            }
        )

    def test_account_notices_credentials(self):
        """Only the warning: the account is behind on nothing."""
        self._account_of_the_notices(need_update=True)
        self.start_tour(
            DASHBOARD_URL,
            "social_media_sync.account_notices_credentials",
            login="admin",
        )

    def test_account_notices_import(self):
        """Only the notice: the token works and the publications are behind."""
        self._account_of_the_notices(posts_need_import=True)
        self.start_tour(
            DASHBOARD_URL,
            "social_media_sync.account_notices_import",
            login="admin",
        )

    def test_account_notices_both(self):
        """The two at once, each with its own text."""
        self._account_of_the_notices(need_update=True, posts_need_import=True)
        self.start_tour(
            DASHBOARD_URL,
            "social_media_sync.account_notices_both",
            login="admin",
        )

    def test_account_notices_none(self):
        """Nothing pending, nothing announced."""
        self._account_of_the_notices()
        self.start_tour(
            DASHBOARD_URL,
            "social_media_sync.account_notices_none",
            login="admin",
        )

    def test_update_says_nothing_was_imported(self):
        """The button refreshed the figures and had no account to read.

        Announcing publications it did not bring in is what would make the
        button look broken the next time an account really is behind.
        """
        self._account_of_the_notices()
        # Every connector can tell what moved, and nothing moved: the
        # narrowing keeps no account and the import is never asked for. The
        # figures are refreshed all the same, which is the case under test —
        # they cost a fixed number of calls and move on their own.
        self.patch(
            type(self.SocialAccount), "_detects_pending_posts", lambda self: True
        )
        self.patch(type(self.SocialAccount), "_refresh_statistics", lambda self: True)
        self.start_tour(
            DASHBOARD_URL,
            "social_media_sync.update_without_new_publications",
            login="admin",
        )
