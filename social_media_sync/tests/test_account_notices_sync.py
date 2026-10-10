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

    def _update_reads_the_account(self, account, created):
        """Patch the import of *Update* to read ``account`` only.

        The figures are refreshed all the same, and the publications of the
        window answer nothing: what the tour asserts must not depend on the
        accounts the database it runs against holds.

        :param account: the account the import reads.
        :param created: how many publications the import brings in.
        """
        SocialAccount = type(self.SocialAccount)

        def import_publications(accounts, post_id, domain, imported=None):
            for index in range(created):
                accounts.env["social.post.account"].create(
                    {
                        "account_id": account.id,
                        "message": "Imported publication %s" % index,
                    }
                )
            if imported is not None:
                imported.add(account.id)
            return []

        self.patch(SocialAccount, "_update_posts_statistics", import_publications)
        self.patch(SocialAccount, "_refresh_statistics", lambda self: True)
        self.patch(SocialAccount, "_refresh_window_statistics", lambda self: False)

    def test_update_says_new_publications_were_imported(self):
        """The import read the account and brought publications in."""
        account = self._account_of_the_notices()
        self._update_reads_the_account(account, created=1)
        self.start_tour(
            DASHBOARD_URL,
            "social_media_sync.update_with_new_publications",
            login="admin",
        )

    def test_update_says_nothing_was_imported(self):
        """The import read the account and found nothing new.

        Announcing publications it did not bring in is what would make the
        button look broken the next time an account really is behind.
        """
        account = self._account_of_the_notices()
        self._update_reads_the_account(account, created=0)
        self.start_tour(
            DASHBOARD_URL,
            "social_media_sync.update_without_new_publications",
            login="admin",
        )

    def test_update_without_import_words_the_figures(self):
        """No account to import: the notice is the one of the figures."""
        self._account_of_the_notices()
        # Every connector can tell what moved, and nothing moved: the
        # narrowing keeps no account and the import is never asked for. The
        # figures are refreshed all the same — they cost a fixed number of
        # calls and move on their own.
        SocialAccount = type(self.SocialAccount)
        self.patch(SocialAccount, "_detects_pending_posts", lambda self: True)
        self.patch(SocialAccount, "_refresh_statistics", lambda self: True)
        self.patch(SocialAccount, "_refresh_window_statistics", lambda self: False)
        self.start_tour(
            DASHBOARD_URL,
            "social_media_sync.update_without_import",
            login="admin",
        )
