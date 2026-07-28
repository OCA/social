# Copyright 2025 Binhex <https://www.binhex.cloud>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import json

from odoo.tests.common import HttpCase, tagged

from odoo.addons.social_media_base.tests.test_social_common import (
    TestSocialMediaBaseCommon,
)


@tagged("post_install", "-at_install")
class TestThreadControllerSocial(HttpCase, TestSocialMediaBaseCommon):
    def setUp(self):
        super().setUp()
        self.authenticate(None, None)

    def _call_message_post(self, thread_id):
        payload = {
            "jsonrpc": "2.0",
            "method": "call",
            "params": {
                "thread_model": "social.post.account",
                "thread_id": thread_id,
                "post_data": {"body": "Comment"},
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
