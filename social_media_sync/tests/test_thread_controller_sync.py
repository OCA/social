# Copyright 2026 Binhex <https://www.binhex.cloud>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import json

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

    def _call_session_info(self):
        payload = {"jsonrpc": "2.0", "method": "call", "params": {}}
        response = self.url_open(
            "/web/session/get_session_info",
            data=json.dumps(payload),
            headers={"Content-Type": "application/json"},
        )
        return response.json()["result"]

    def test_session_info_delivers_the_kept_notification(self):
        self._authenticate_social_manager()
        notification = {"message": "kept message", "message_type": "success"}
        self.session["social_media_notification"] = notification
        odoo.http.root.session_store.save(self.session)
        result = self._call_session_info()
        self.assertEqual(result["social_media_notification"], notification)
        self.assertNotIn("social_media_notification", self._call_session_info())
