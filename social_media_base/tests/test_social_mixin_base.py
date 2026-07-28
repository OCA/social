# Copyright 2025 Binhex <https://www.binhex.cloud>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from unittest.mock import patch

from odoo.exceptions import AccessError

from odoo.addons.mail.tests.common import mail_new_test_user
from odoo.addons.social_media_base.tests.test_social_common import (
    TestSocialMediaBaseCommon,
)


class TestSocialMediaBaseMixin(TestSocialMediaBaseCommon):
    def _capture_notification(self, **kwargs):
        sent = []
        with patch.object(
            type(self.env["bus.bus"]),
            "_sendone",
            autospec=True,
            side_effect=lambda bus, channel, notif_type, message: sent.append(
                (channel, notif_type, message)
            ),
        ):
            self.SocialMediaBaseMixin._notify_user_client(**kwargs)
        return sent

    def test_notify_user_client_escapes_html(self):
        sent = self._capture_notification(
            notif_type="social_kanban_danger",
            notif_message="<script>alert(1)</script>",
            media="linkedin",
        )
        self.assertEqual(len(sent), 1)
        message = sent[0][2]["message"]
        self.assertNotIn("<script>", message)
        self.assertIn("&lt;script&gt;", message)

    def test_notify_user_client_without_notif_type(self):
        sent = self._capture_notification(
            notif_message="boom",
            media="linkedin",
        )
        self.assertEqual(len(sent), 1)
        self.assertEqual(sent[0][2]["message_type"], "danger")

    def test_notify_user_client_without_message(self):
        sent = self._capture_notification(notif_type="social_kanban_danger")
        self.assertEqual(sent, [])

    def test_access_token_restricted_to_system_group(self):
        user = mail_new_test_user(
            self.env, login="social_base_user", groups="base.group_user"
        )
        account = self.social_account_id.with_user(user)
        with self.assertRaises(AccessError):
            account.read(["access_token"])
        with self.assertRaises(AccessError):
            account.read(["refresh_access_token"])
        self.assertFalse(self.social_account_id.sudo().access_token)

    def test_wizard_csrf_state_token_computes_without_error(self):
        wizard = self.WizardAccount.create({"media_id": self.social_media_id.id})
        wizard._compute_csrf_state_token()
        self.assertFalse(wizard.csrf_state_token)
