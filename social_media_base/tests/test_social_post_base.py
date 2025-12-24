# Copyright 2025 Binhex <https://www.binhex.cloud>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from datetime import datetime, timedelta
from unittest.mock import patch

from odoo.fields import Command

from odoo.addons.social_media_base.tests.test_social_common import (
    TestSocialMediaBaseCommon,
)

from .test_social_common import (
    PATCH_POST,
)


class TestSocialPostBase(TestSocialMediaBaseCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

    def test_compute_send_post_date(self):
        self.social_post_id.send_post = "schedule"
        self.social_post_id._compute_send_post_date()
        self.assertEqual(
            self.social_post_id.send_post_date.strftime("%Y-%m-%d"),
            (datetime.now() + timedelta(hours=1)).strftime("%Y-%m-%d"),
        )
        self.assertEqual(self.social_post_id.state, "planned")

    def test_compute_post_statistics(self):
        self.social_post_id._compute_post_statistics()
        self.assertEqual(self.social_post_id.count_post_likes, 0)
        self.assertEqual(self.social_post_id.count_post_shares, 0)
        self.assertEqual(self.social_post_id.count_post_likes, 0)
        self.assertEqual(self.social_post_id.count_post_engagement, 0)
        self.assertEqual(self.social_post_id.count_post_impression, 0)
        self.assertEqual(self.social_post_id.count_post_comments, 0)
        self.assertEqual(self.social_post_id.count_post_interactions, 0)

    @patch(PATCH_POST.format("_action_create_post_account"))
    def test_run_send_post(self, mock_action_create_post_account):
        self.social_post_id._run_send_post()
        mock_action_create_post_account.assert_called_once()

    def test_action_create_post_account(self):
        fake_post_account = [
            Command.create(
                {
                    "post_id": self.social_post_id.id,
                    "account_id": self.social_post_account_id.account_id.id,
                    "state": "ready",
                    "message": self.test_message,
                }
            )
        ]
        with (
            patch.object(
                type(self.social_post_id),
                "_prepare_post_account_values",
                autospec=True,
                return_value=fake_post_account,
            ),
            patch.object(
                type(self.social_post_account_id),
                "_action_post",
                autospec=True,
            ) as mock_action_post,
        ):
            self.social_post_id._action_create_post_account()
            mock_action_post.assert_called_once_with(
                self.SocialPostAccount,
                post_id=self.social_post_id,
            )
            self.assertEqual(self.social_post_id.state, "published")
            self.assertEqual(len(self.social_post_id.post_account_ids), 2)

    def test_compute_display_name(self):
        self.social_post_id._compute_display_name()
        self.assertEqual(self.social_post_id.display_name, "Post on Linkedin")

    def test_comments(self):
        result = self.social_post_account_id.create_comment({})
        self.assertIsNone(result)

        result = self.social_post_account_id.get_comments()
        self.assertIsInstance(result, dict)
        self.assertEqual(result, {"success": False, "data": []})

    def test_action_post(self):
        result = self.social_post_account_id._action_post({})
        self.assertIsNone(result)

    def test_delete_post_account_deletes_post_when_last_link(self):
        post = self.SocialPost.create(
            {
                "message": self.test_message,
                "account_ids": [Command.set(self.social_account_id.ids)],
            }
        )
        post_account = self.SocialPostAccount.create(
            {
                "message": self.test_message,
                "account_id": self.social_account_id.id,
                "post_id": post.id,
            }
        )
        with patch.object(
            type(post_account), "_delete_post_account", autospec=True
        ) as mocked_hook:
            action = post_account.delete_post_account()
            mocked_hook.assert_called_once_with(post_account)
        self.assertFalse(self.SocialPostAccount.browse(post_account.id).exists())
        self.assertFalse(self.SocialPost.browse(post.id).exists())
        self.assertEqual(action["type"], "ir.actions.client")
        self.assertEqual(action["tag"], "display_notification")
        params = action["params"]
        self.assertEqual(params["type"], "success")
        self.assertIn("Post deleted", params["title"])
        self.assertIn(self.social_account_id.name, params["title"])
        self.assertEqual(params["message"], "The post was successfully deleted.")
        self.assertEqual(params["next"], {"type": "ir.actions.client", "tag": "reload"})

    def test_delete_post_account_when_other_links_exist(self):
        post = self.SocialPost.create(
            {
                "message": self.test_message,
                "account_ids": [Command.set(self.social_account_id.ids)],
            }
        )
        post_account1 = self.SocialPostAccount.create(
            {
                "message": self.test_message,
                "account_id": self.social_account_id.id,
                "post_id": post.id,
            }
        )
        post_account2 = self.SocialPostAccount.create(
            {
                "message": self.test_message,
                "account_id": self.social_account_id.id,
                "post_id": post.id,
            }
        )
        with patch.object(type(post_account1), "_delete_post_account", autospec=True):
            action = post_account1.delete_post_account()
        self.assertFalse(self.SocialPostAccount.browse(post_account1.id).exists())
        self.assertTrue(self.SocialPostAccount.browse(post_account2.id).exists())
        self.assertTrue(self.SocialPost.browse(post.id).exists())
        self.assertEqual(action["type"], "ir.actions.client")
        self.assertEqual(action["tag"], "display_notification")