# Copyright 2025 Binhex <https://www.binhex.cloud>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from datetime import datetime, timedelta
from unittest.mock import patch

from odoo.fields import Command
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT

from odoo.addons.social_media_base.tests.test_social_common import (
    TestSocialMediaBaseCommon,
)

from .test_social_common import PATCH_POST


class TestSocialPostBase(TestSocialMediaBaseCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

    def test_compute_send_post_date(self):
        self.social_post_id.send_post = "schedule"
        self.social_post_id._compute_send_post_date()
        self.assertEqual(
            self.social_post_id.send_post_date.strftime(DEFAULT_SERVER_DATE_FORMAT),
            (datetime.now() + timedelta(hours=1)).strftime(DEFAULT_SERVER_DATE_FORMAT),
        )
        self.assertEqual(self.social_post_id.state, "planned")

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
            self.assertEqual(self.social_post_id.state, "publishing")
            self.assertEqual(len(self.social_post_id.post_account_ids), 2)

    def test_compute_display_name(self):
        self.social_post_id._compute_display_name()
        self.assertIn("Linkedin", self.social_post_id.display_name)

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

    def test_action_create_post_account_mixed_results(self):
        post = self.SocialPost.create(
            {
                "message": self.test_message,
                "account_ids": [Command.set(self.social_account_id.ids)],
            }
        )
        fake_post_accounts = [
            Command.create(
                {
                    "account_id": self.social_account_id.id,
                    "state": "ready",
                    "message": self.test_message,
                }
            ),
            Command.create(
                {
                    "account_id": self.social_account_id.id,
                    "state": "ready",
                    "message": self.test_message,
                }
            ),
        ]

        def fake_action_post(records, post_id=None):
            post_id.post_account_ids[0].state = "posted"
            post_id.post_account_ids[1].state = "failed"

        with (
            patch.object(
                type(post),
                "_prepare_post_account_values",
                autospec=True,
                return_value=fake_post_accounts,
            ),
            patch.object(
                type(self.social_post_account_id),
                "_action_post",
                autospec=True,
                side_effect=fake_action_post,
            ),
        ):
            post._action_create_post_account()
        self.assertEqual(post.state, "publishing")

    def test_compute_message_info_default(self):
        self.assertFalse(self.social_post_id.message_info)

    def test_count_post_impression_uses_impression_count(self):
        self.social_post_account_id.write({"impression_count": 7, "engagement": 3.5})
        self.assertEqual(self.social_post_id.count_post_impression, 7)
        self.assertEqual(self.social_post_id.count_post_engagement, 3.5)

    def test_media_attachments_are_anchored_to_the_publication(self):
        attachment = self.env["ir.attachment"].create(
            {
                "name": "urn:li:digitalmediaAsset:TEST",
                "type": "binary",
                "res_model": "social.post.account",
                "datas": b"ZmFrZS1pbWFnZQ==",
            }
        )
        self.assertFalse(attachment.res_id)
        post_account = self.SocialPostAccount.create(
            {
                "message": "With an image",
                "account_id": self.social_account_id.id,
                "image_ids": [Command.set(attachment.ids)],
            }
        )
        self.assertEqual(
            (attachment.res_model, attachment.res_id),
            ("social.post.account", post_account.id),
            "The attachment must point at its publication, otherwise only "
            "the system administrators can read it",
        )

    def test_media_attachments_anchored_on_write(self):
        post_account = self.SocialPostAccount.create(
            {
                "message": "Without an image yet",
                "account_id": self.social_account_id.id,
            }
        )
        attachment = self.env["ir.attachment"].create(
            {
                "name": "urn:li:digitalmediaAsset:TEST2",
                "type": "binary",
                "res_model": "social.post.account",
                "datas": b"ZmFrZS1pbWFnZQ==",
            }
        )
        post_account.write({"image_ids": [Command.set(attachment.ids)]})
        self.assertEqual(attachment.res_id, post_account.id)

    def test_get_medias_account_finds_medias_of_other_users(self):
        attachment = self.env["ir.attachment"].create(
            {
                "name": "urn:li:digitalmediaAsset:SHARED",
                "type": "binary",
                "res_model": "social.post.account",
                "res_id": self.social_post_account_id.id,
                "datas": b"ZmFrZS1pbWFnZQ==",
            }
        )
        other_user = self.env["res.users"].create(
            {
                "name": "Other social user",
                "login": "other_media_user_test",
                "group_ids": [
                    Command.set(
                        [
                            self.env.ref("base.group_user").id,
                            self.env.ref(
                                "social_media_base.group_social_media_user"
                            ).id,
                        ]
                    )
                ],
            }
        )
        self.assertEqual(
            self.social_post_account_id.with_user(other_user)._get_medias_account(
                [attachment.name]
            ),
            [attachment.name],
            "The medias already downloaded must be found whoever runs the "
            "synchronization, otherwise every run creates a duplicate",
        )
