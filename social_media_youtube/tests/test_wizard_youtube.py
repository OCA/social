# Copyright 2026 Domatix <https://www.domatix.cloud>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from unittest.mock import patch

from odoo.tools import mute_logger

from .common import YouTubeCommon

ACCOUNT = "odoo.addons.social_media_youtube.models.social_account.SocialAccount"
LOGGER = "odoo.addons.social_media_youtube.wizards.wizard_social_account"


class TestWizardYouTube(YouTubeCommon):
    """The YouTube steps of the account association wizard."""

    def test_redirect_uri(self):
        self.assertEqual(
            self._create_wizard()._get_url_redirect(), "/social_youtube/callback"
        )
        self.assertIsNone(self._create_wizard(self.other_media)._get_url_redirect())

    def test_csrf_state_token(self):
        self.assertTrue(self._create_wizard()._get_csrf_state_token())
        self.assertIsNone(self._create_wizard(self.other_media)._get_csrf_state_token())

    def test_url_authorize(self):
        wizard = self._create_wizard(
            youtube_client_id="client-id", youtube_client_secret="client-secret"
        )
        action = wizard._get_url_authorize()
        self.assertEqual(action["type"], "ir.actions.act_url")
        self.assertIn("accounts.google.com", action["url"])
        self.assertIn("client_id=client-id", action["url"])
        self.assertIn("access_type=offline", action["url"])
        self.assertTrue(wizard.csrf_state_token)

    @mute_logger(LOGGER)
    def test_url_authorize_failure(self):
        wizard = self._create_wizard(
            youtube_client_id="client-id", youtube_client_secret="client-secret"
        )
        with patch.object(
            type(wizard), "_set_csrf_state_token", side_effect=Exception("boom")
        ):
            action = wizard._get_url_authorize()
        self.assertEqual(action["type"], "ir.actions.client")
        self.assertEqual(action["tag"], "display_notification")

    def test_add_account_redirects_to_youtube(self):
        wizard = self._create_wizard(
            youtube_client_id="client-id", youtube_client_secret="client-secret"
        )
        self.assertEqual(wizard._action_add_account()["type"], "ir.actions.act_url")

    def test_add_account_of_another_media(self):
        self.assertIsNone(self._create_wizard(self.other_media)._action_add_account())

    def test_url_authorize_of_another_media(self):
        self.assertIsNone(self._create_wizard(self.other_media)._get_url_authorize())

    def test_update_account_with_new_keys(self):
        account = self._create_account()
        wizard = self._create_wizard(
            account_id=account.id,
            youtube_client_id="client-id",
            youtube_client_secret="client-secret",
            update_keys=True,
        )
        self.assertEqual(wizard._update_account()["type"], "ir.actions.act_url")

    def test_update_account_with_a_new_token(self):
        account = self._create_account()
        wizard = self._create_wizard(
            account_id=account.id,
            youtube_client_id="client-id",
            youtube_client_secret="client-secret",
            update_token=True,
        )
        self.assertEqual(wizard._update_account()["type"], "ir.actions.act_url")

    @patch(f"{ACCOUNT}._update_account_data")
    def test_update_account_refreshes_its_data(self, mock_update):
        account = self._create_account()
        wizard = self._create_wizard(account_id=account.id)
        self.assertIsNone(wizard._update_account())
        mock_update.assert_called_once()

    def test_update_account_of_another_media(self):
        self.assertIsNone(self._create_wizard(self.other_media)._update_account())
