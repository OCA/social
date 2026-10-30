# Copyright 2026 Binhex <https://www.binhex.cloud>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from unittest.mock import MagicMock, patch

from markupsafe import Markup

from odoo.exceptions import AccessError
from odoo.tests.common import tagged

from odoo.addons.mail.tests.common import mail_new_test_user
from odoo.addons.social_media_base.tests.test_social_common import (
    PATCH_MIXIN_REQUEST,
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

    def test_format_user_notification_announces_the_failures_in_bold(self):
        message = self.SocialMediaBaseMixin._format_user_notification(
            "The token was revoked.", media="linkedin"
        )
        self.assertIn("<b>ERROR:</b> The token was revoked.", message)

    def test_format_user_notification_of_anything_else_has_no_empty_tag(self):
        """Only a failure is announced, the rest keeps its message alone."""
        message = self.SocialMediaBaseMixin._format_user_notification(
            "The token is valid.", media="linkedin", message_type="success"
        )
        self.assertNotIn("<b></b>", message)
        self.assertNotIn("ERROR:", message)
        self.assertIn("The token is valid.", message)

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

    def test_notify_user_session_escapes_html(self):
        mock_request = MagicMock(session={})
        with patch(PATCH_MIXIN_REQUEST, new=mock_request):
            self.SocialMediaBaseMixin._notify_user_session("<script>alert(1)</script>")
        stored = mock_request.session["social_media_notification"][0]
        self.assertNotIn("<script>", stored["message"])
        self.assertIn("&lt;script&gt;", stored["message"])
        self.assertEqual(stored["message_type"], "danger")

    def test_notify_user_session_keeps_markup(self):
        mock_request = MagicMock(session={})
        with patch(PATCH_MIXIN_REQUEST, new=mock_request):
            self.SocialMediaBaseMixin._notify_user_session(
                Markup("<b>ok</b>"), message_type="success"
            )
        stored = mock_request.session["social_media_notification"][0]
        self.assertEqual(stored["message"], "<b>ok</b>")
        self.assertEqual(stored["message_type"], "success")

    def test_notify_user_session_keeps_every_message(self):
        """A callback reporting twice must not lose what it said first."""
        mock_request = MagicMock(session={})
        with patch(PATCH_MIXIN_REQUEST, new=mock_request):
            self.SocialMediaBaseMixin._notify_user_session("first")
            self.SocialMediaBaseMixin._notify_user_session(
                "second", message_type="success"
            )
        kept = mock_request.session["social_media_notification"]
        self.assertEqual([notif["message"] for notif in kept], ["first", "second"])
        self.assertEqual(
            [notif["message_type"] for notif in kept], ["danger", "success"]
        )

    def test_notify_user_takes_the_session_on_an_oauth_callback(self):
        """The redirect of a callback outruns the bus, so nothing goes there."""
        mock_request = MagicMock(session={})
        with patch(PATCH_MIXIN_REQUEST, new=mock_request), patch.object(
            type(self.env["bus.bus"]), "_sendone", autospec=True
        ) as mock_sendone:
            self.SocialMediaBaseMixin.with_context(
                social_media_oauth_callback=True
            )._notify_user(
                notif_type="social_kanban_danger",
                notif_message="boom",
                media="linkedin",
            )
        mock_sendone.assert_not_called()
        kept = mock_request.session["social_media_notification"]
        self.assertEqual(len(kept), 1)
        self.assertIn("boom", kept[0]["message"])
        self.assertEqual(kept[0]["message_type"], "danger")

    def test_notify_user_takes_the_bus_without_the_callback_mark(self):
        mock_request = MagicMock(session={})
        sent = []
        with patch(PATCH_MIXIN_REQUEST, new=mock_request), patch.object(
            type(self.env["bus.bus"]),
            "_sendone",
            autospec=True,
            side_effect=lambda bus, channel, notif_type, message: sent.append(message),
        ):
            self.SocialMediaBaseMixin._notify_user(
                notif_type="social_kanban_danger",
                notif_message="boom",
                media="linkedin",
            )
        self.assertEqual(len(sent), 1)
        self.assertIn("boom", sent[0]["message"])
        self.assertNotIn("social_media_notification", mock_request.session)

    def test_notify_user_of_a_callback_without_message_keeps_nothing(self):
        mock_request = MagicMock(session={})
        with patch(PATCH_MIXIN_REQUEST, new=mock_request):
            self.SocialMediaBaseMixin.with_context(
                social_media_oauth_callback=True
            )._notify_user(notif_type="social_kanban_danger")
        self.assertNotIn("social_media_notification", mock_request.session)

    def test_wizard_csrf_state_token_computes_without_error(self):
        wizard = self.WizardAccount.create({"media_id": self.social_media_id.id})
        wizard._set_csrf_state_token()
        self.assertFalse(wizard.csrf_state_token)


@tagged("post_install", "-at_install")
class TestSocialMediaBaseMixinUsers(TestSocialMediaBaseCommon):
    """Users are created here, so every module has to be in the registry."""

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
