# Copyright 2026 Domatix <https://www.domatix.cloud>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from unittest.mock import patch

from odoo.tools import mute_logger

from .common import InstagramCommon

ACCOUNT = "odoo.addons.social_media_instagram.models.social_account.SocialAccount"
LOGGER = "odoo.addons.social_media_instagram.wizards.wizard_social_account"


class TestWizardInstagram(InstagramCommon):
    """The Instagram steps of the account association wizard."""

    def test_redirect_uri(self):
        self.assertEqual(
            self._create_wizard()._get_url_redirect(), "/social_instagram/callback"
        )
        self.assertIsNone(self._create_wizard(self.other_media)._get_url_redirect())

    def test_csrf_state_token(self):
        self.assertTrue(self._create_wizard()._get_csrf_state_token())
        self.assertIsNone(self._create_wizard(self.other_media)._get_csrf_state_token())

    def test_url_authorize(self):
        wizard = self._create_wizard(
            instagram_app_id="app-id", instagram_app_secret="app-secret"
        )
        action = wizard._get_url_authorize()
        self.assertEqual(action["type"], "ir.actions.act_url")
        self.assertIn("instagram.com", action["url"])
        self.assertIn("client_id=app-id", action["url"])
        self.assertTrue(wizard.csrf_state_token)

    @mute_logger(LOGGER)
    def test_url_authorize_failure(self):
        wizard = self._create_wizard(
            instagram_app_id="app-id", instagram_app_secret="app-secret"
        )
        with patch.object(
            type(wizard), "_set_csrf_state_token", side_effect=Exception("boom")
        ):
            action = wizard._get_url_authorize()
        self.assertEqual(action["type"], "ir.actions.client")
        self.assertEqual(action["tag"], "display_notification")

    def test_add_account_redirects_to_instagram(self):
        wizard = self._create_wizard(
            instagram_app_id="app-id", instagram_app_secret="app-secret"
        )
        self.assertEqual(wizard._action_add_account()["type"], "ir.actions.act_url")

    def test_add_account_of_another_media(self):
        self.assertIsNone(self._create_wizard(self.other_media)._action_add_account())

    def test_update_account_with_new_keys(self):
        account = self._create_account()
        wizard = self._create_wizard(
            account_id=account.id,
            instagram_app_id="app-id",
            instagram_app_secret="app-secret",
            update_keys=True,
        )
        self.assertEqual(wizard._update_account()["type"], "ir.actions.act_url")

    def test_update_account_with_a_new_token(self):
        account = self._create_account()
        wizard = self._create_wizard(
            account_id=account.id,
            instagram_app_id="app-id",
            instagram_app_secret="app-secret",
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

    def test_url_authorize_of_another_media(self):
        self.assertIsNone(self._create_wizard(self.other_media)._get_url_authorize())
