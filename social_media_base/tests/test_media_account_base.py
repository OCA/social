# Copyright 2025 Kencove (https://www.kencove.com/)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo.addons.social_media_base.tests.test_social_common import (
    TestSocialMediaBaseCommon,
)


class TestSocialMediaBase(TestSocialMediaBaseCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

    def test_action_like_comment(self):
        result = self.SocialPostAccount.action_like_comment()
        self.assertEqual(result, {"success": True, "message": ""})

    def test_filter_by_media_types(self):
        result = self.SocialPostAccount.filter_by_media_types([])
        self.assertEqual(len(result), 0)

    def _patch_bus(self):
        bus = self.env["bus.bus"]
        self._calls = []

        def fake_sendone(self_rec, target, notif_type, payload):
            self._calls.append((target, notif_type, payload))
            return None

        self._orig_sendone = type(bus)._sendone
        type(bus)._sendone = fake_sendone

    def _restore_bus(self):
        type(self.env["bus.bus"])._sendone = self._orig_sendone

    def setUp(self):
        super().setUp()
        self._patch_bus()

    def tearDown(self):
        self._restore_bus()
        super().tearDown()

    def test_notify_with_media_danger_includes_error_and_html(self):
        self.SocialAccount._notify_user_client(
            target="notif_channel",
            notif_type="notif_danger",
            notif_message="Error",
            media="x",
            social_name="My page",
        )
        self.assertEqual(len(self._calls), 1)
        _, notif_type, payload = self._calls[0]
        self.assertEqual(notif_type, "notif_danger")
        self.assertEqual(payload.get("message_type"), "danger")
        msg = str(payload.get("message"))
        self.assertIn("X My page", msg)
        self.assertIn("<b>ERROR:</b>", msg)
        self.assertIn("Error", msg)

    def test_notify_with_media_info_without_error_label(self):
        self.SocialAccount._notify_user_client(
            target="notif_channel",
            notif_type="notif_info",
            notif_message="Message info",
            media="twitter",
            social_name=False,
        )
        self.assertEqual(len(self._calls), 1)
        _, notif_type, payload = self._calls[0]
        self.assertEqual(notif_type, "notif_info")
        self.assertEqual(payload.get("message_type"), "info")
        msg = str(payload.get("message"))
        self.assertIn("TWITTER", msg)
        self.assertNotIn("ERROR:", msg)
        self.assertIn("Message info", msg)

    def test_get_result_none(self):
        result = self.WizardAccount._get_csrf_state_token()
        self.assertEqual(result, None)
        result = self.WizardAccount._get_url_redirect()
        self.assertEqual(result, None)
        result = self.WizardAccount._action_add_account()
        self.assertEqual(result, None)
        result = self.WizardAccount._update_account()
        self.assertEqual(result, None)
        result = self.WizardAccount.update_account()
        self.assertEqual(result, None)
        result = self.WizardAccount._action_valid_add_account()
        self.assertTrue(result)
