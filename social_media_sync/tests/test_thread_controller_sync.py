# Copyright 2026 Binhex <https://www.binhex.cloud>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import json
from unittest.mock import patch

import odoo
from odoo.tests.common import HttpCase, tagged

from .test_social_sync_common import TestSocialMediaSyncCommon


@tagged("post_install", "-at_install")
class TestThreadControllerSocial(HttpCase, TestSocialMediaSyncCommon):
    def setUp(self):
        super().setUp()
        self.authenticate(None, None)

    def _call_message_post(
        self, thread_id, thread_model="social.post.account", post_data=None
    ):
        payload = {
            "jsonrpc": "2.0",
            "method": "call",
            "params": {
                "thread_model": thread_model,
                "thread_id": thread_id,
                "post_data": post_data or {"body": "Comment"},
            },
        }
        response = self.url_open(
            "/mail/message/post",
            data=json.dumps(payload),
            headers={"Content-Type": "application/json"},
        )
        return response.json()

    def test_public_user_cannot_comment(self):
        result = self._call_message_post(self.social_post_account_id.id)
        self.assertIn("error", result)
        self.assertIn("AccessError", result["error"]["data"].get("name", ""))

    def test_missing_post_account_returns_none(self):
        result = self._call_message_post(999999999)
        self.assertNotIn("error", result)
        self.assertIsNone(result.get("result"))

    def _authenticate_social_manager(self):
        user = self.env["res.users"].create(
            {
                "name": "Social manager",
                "login": "social_manager_http",
                "password": "social_manager_http",
                "email": "social.manager@test.example.com",
                "groups_id": [
                    (
                        6,
                        0,
                        [
                            self.env.ref("base.group_user").id,
                            self.env.ref(
                                "social_media_base.group_social_media_manager"
                            ).id,
                        ],
                    )
                ],
            }
        )
        self.authenticate("social_manager_http", "social_manager_http")
        return user

    def test_other_thread_models_use_the_standard_behaviour(self):
        self._authenticate_social_manager()
        result = self._call_message_post(
            self.social_post_id.id, thread_model="social.post"
        )
        message = result["result"]
        self.assertEqual(message["model"], "social.post")
        self.assertEqual(message["res_id"], self.social_post_id.id)

    def test_manager_can_comment(self):
        self._authenticate_social_manager()
        result = self._call_message_post(self.social_post_account_id.id)
        self.assertNotIn("error", result)
        author = result["result"]["author"]
        self.assertEqual(author["type"], "partner")
        self.assertTrue(author["user"]["isInternalUser"])

    def test_the_notification_says_which_publication_it_is_about(self):
        """The bus channel is the partner, so the payload names the post.

        A user with more than one dialog open hears every publication on the
        same channel, and only the reference tells a dialog its own comment
        from one published somewhere else.
        """
        self._authenticate_social_manager()
        with patch.object(
            type(self.env["bus.bus"]), "_sendone", autospec=True
        ) as mock_sendone:
            self._call_message_post(self.social_post_account_id.id)
        payloads = [
            call.args[3]
            for call in mock_sendone.call_args_list
            if call.args[2] == "comments"
        ]
        self.assertEqual(len(payloads), 1)
        self.assertEqual(payloads[0]["post_account_id"], self.social_post_account_id.id)

    def _call_session_info(self):
        payload = {"jsonrpc": "2.0", "method": "call", "params": {}}
        response = self.url_open(
            "/web/session/get_session_info",
            data=json.dumps(payload),
            headers={"Content-Type": "application/json"},
        )
        return response.json()["result"]

    def test_session_info_delivers_every_kept_notification(self):
        """The callbacks keep a list, and the whole list is delivered once."""
        self._authenticate_social_manager()
        notifications = [
            {"message": "the series could not be read", "message_type": "danger"},
            {"message": "kept message", "message_type": "success"},
        ]
        self.session["social_media_notification"] = notifications
        odoo.http.root.session_store.save(self.session)
        result = self._call_session_info()
        self.assertEqual(result["social_media_notification"], notifications)
        self.assertNotIn("social_media_notification", self._call_session_info())
