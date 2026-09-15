# Copyright 2026 Binhex <https://www.binhex.cloud>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).


from unittest.mock import patch

from odoo.exceptions import UserError

from odoo.addons.social_media_linkedin.social_linkedin_utils import (
    _SCOPE_OPTIONAL_LINKEDIN,
)
from odoo.addons.social_media_linkedin.tests.test_common_linkedin import (
    PATCH_ACCOUNT_LINKEDIN,
    RECENT_STATISTICS_LINKEDIN,
)

from ..social_linkedin_sync_utils import _SCOPE_OPTIONAL_SYNC_LINKEDIN
from .test_sync_linkedin_common import TestSocialSyncCommonLinkedin

GRANTED_LINKEDIN = "rw_organization_admin, w_organization_social"
GRANTED_WITH_IMPORT_LINKEDIN = f"{GRANTED_LINKEDIN}, r_organization_social"


class TestSocialSyncScopesLinkedin(TestSocialSyncCommonLinkedin):
    """The account that cannot import its history says so."""

    def _mark_the_page_as_imported(self, accounts=None, statistics=None):
        accounts = accounts or self.SocialAccountLinkedin
        accounts.linkedin_statistics_checkpoint = (
            accounts._linkedin_statistics_checkpoint(
                statistics or RECENT_STATISTICS_LINKEDIN
            )
        )

    def _messages_of(self, account):
        return self.env["mail.message"].search(
            [("model", "=", account._name), ("res_id", "=", account.id)]
        )

    def test_missing_sync_scopes_of_an_authorized_account(self):
        """An account granted the scope is missing nothing."""
        account = self.SocialAccountLinkedin
        account.sudo().linkedin_granted_scopes = GRANTED_WITH_IMPORT_LINKEDIN
        self.assertEqual(account.linkedin_missing_sync_scopes, "")

    def test_missing_sync_scopes_without_reported_scopes(self):
        """LinkedIn reported nothing yet, so nothing is claimed to be wrong."""
        account = self.SocialAccountLinkedin
        account.sudo().linkedin_granted_scopes = False
        self.assertEqual(account.linkedin_missing_sync_scopes, "")

    def test_missing_sync_scopes_of_a_token_issued_before_the_module(self):
        account = self.SocialAccountLinkedin
        account.sudo().linkedin_granted_scopes = GRANTED_LINKEDIN
        self.assertEqual(account.linkedin_missing_sync_scopes, "r_organization_social")

    def test_missing_sync_scopes_of_another_social_media(self):
        """An account of another network never answers a LinkedIn scope."""
        self.assertEqual(self.social_account_id.linkedin_missing_sync_scopes, "")

    def test_import_linkedin_posts_refuses_without_the_scope(self):
        """The import says which permission is missing instead of calling."""
        account = self.SocialAccountLinkedin
        account.sudo().linkedin_granted_scopes = GRANTED_LINKEDIN
        with patch(
            PATCH_ACCOUNT_LINKEDIN.format("_request_linkedin"), autospec=True
        ) as mock_request:
            with self.assertRaises(UserError) as error:
                account._import_linkedin_posts()
        self.assertIn("r_organization_social", str(error.exception))
        mock_request.assert_not_called()

    def test_import_linkedin_posts_runs_with_the_scope(self):
        """The guard lets an authorized account through."""
        account = self.SocialAccountLinkedin
        account.sudo().linkedin_granted_scopes = GRANTED_WITH_IMPORT_LINKEDIN
        account._check_linkedin_scopes(["r_organization_social"])

    def test_check_updates_warns_instead_of_raising(self):
        """The cron cannot raise: it warns the responsible user and goes on."""
        account = self.SocialAccountLinkedin
        self._isolate_linkedin_account()
        self._mark_the_page_as_imported()
        account.sudo().linkedin_granted_scopes = GRANTED_LINKEDIN
        before = self._messages_of(account)
        with self._patch_recent_statistics(), patch(
            PATCH_ACCOUNT_LINKEDIN.format("_get_posts"), autospec=True
        ) as mock_get_posts:
            self.assertFalse(self.SocialAccount._run_check_media_updates())
        mock_get_posts.assert_not_called()
        message = self._messages_of(account) - before
        self.assertEqual(len(message), 1)
        self.assertIn("r_organization_social", message.body)
        self.assertIn(account.user_id.partner_id, message.partner_ids)
        self.assertTrue(account.linkedin_sync_scopes_notified)

    def test_check_updates_leaves_posts_need_import_alone(self):
        """The warning must not take the account out of the check for good.

        The check skips every account carrying ``posts_need_import``. Only
        the import clears it, and the import is the very thing that cannot
        run without the scopes.
        """
        account = self.SocialAccountLinkedin
        self._isolate_linkedin_account()
        self._mark_the_page_as_imported()
        account.sudo().linkedin_granted_scopes = GRANTED_LINKEDIN
        account.posts_need_import = False
        with self._patch_recent_statistics(), patch(
            PATCH_ACCOUNT_LINKEDIN.format("_get_posts"), autospec=True
        ):
            self.SocialAccount._run_check_media_updates()
        self.assertFalse(account.posts_need_import)

    def test_check_updates_warns_once(self):
        """A second pass on the same broken account writes nothing more."""
        account = self.SocialAccountLinkedin
        self._isolate_linkedin_account()
        self._mark_the_page_as_imported()
        account.sudo().linkedin_granted_scopes = GRANTED_LINKEDIN
        with self._patch_recent_statistics(), patch(
            PATCH_ACCOUNT_LINKEDIN.format("_get_posts"), autospec=True
        ):
            self.SocialAccount._run_check_media_updates()
            before = self._messages_of(account)
            self.SocialAccount._run_check_media_updates()
        self.assertFalse(self._messages_of(account) - before)

    def test_on_account_associated_lets_it_warn_again(self):
        """A re-authorization that still lacks the scope warns once more."""
        account = self.SocialAccountLinkedin
        account.sudo().linkedin_sync_scopes_notified = True
        # The association refreshes the statistics of the account on its way,
        # which is a call to LinkedIn and not what is under test here.
        with self._patch_reader():
            account._on_account_associated()
        self.assertFalse(account.linkedin_sync_scopes_notified)

    def test_reading_a_thread_refuses_without_the_scope(self):
        """The two reads of a thread name the missing permission."""
        account = self.SocialAccountLinkedin
        account.sudo().linkedin_granted_scopes = GRANTED_LINKEDIN
        publication = self.SocialPostAccountLinkedin
        with patch(
            PATCH_ACCOUNT_LINKEDIN.format("_request_linkedin"), autospec=True
        ) as mock_request:
            for call in (
                publication.get_comments,
                lambda: publication.get_comment_replies("urn:li:comment:(1,2)"),
            ):
                with self.assertRaises(UserError) as error:
                    call()
                self.assertIn("r_organization_social", str(error.exception))
        mock_request.assert_not_called()

    def test_reading_a_thread_of_another_social_media_is_not_guarded(self):
        """A publication of another network never meets a LinkedIn guard."""
        publication = self.social_post_account_id
        publication.account_id.sudo().linkedin_granted_scopes = GRANTED_LINKEDIN
        publication.get_comments()
        publication.get_comment_replies("whatever")


class TestSocialSyncMediaLinkedin(TestSocialSyncCommonLinkedin):
    def test_get_linkedin_scopes_leaves_the_optional_ones_out(self):
        """Neither module asks for the scopes no call of it consumes."""
        scopes = self.media_linkedin_id._get_linkedin_scopes()
        for scope in _SCOPE_OPTIONAL_LINKEDIN + _SCOPE_OPTIONAL_SYNC_LINKEDIN:
            self.assertNotIn(scope, scopes)
