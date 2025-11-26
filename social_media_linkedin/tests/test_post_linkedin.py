# Copyright 2025 Binhex <https://www.binhex.cloud>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import base64
from unittest.mock import MagicMock, patch

from odoo import Command
from odoo.exceptions import ValidationError

from odoo.addons.social_media_base.tests.test_social_common import (
    PATCH_POST_ACCOUNT,
    PATCH_SOCIAL_BASE_UTILS,
)
from odoo.addons.social_media_linkedin.tests.test_common_linkedin import (
    PATCH_ACCOUNT_LINKEDIN,
    PATCH_POST_ACCOUNT_LINKEDIN,
    TestSocialCommonLinkedin,
)


class TestSocialPostLinkedin(TestSocialCommonLinkedin):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

    def create_attachment(self, attach_name="test_exist_image.jpg"):
        return self.env["ir.attachment"].create(
            {
                "name": attach_name,
                "type": "binary",
                "datas": base64.b64encode(b"existing").decode(),
            }
        )

    @patch("odoo.addons.social_media_linkedin.models.social_account.requests.get")
    def test_get_assets_save(self, mock_get):
        fake_content = b"fake image data"
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = fake_content
        mock_get.return_value = mock_response
        media_1 = {
            "media": "test_image.jpg",
            "originalUrl": "https://fake-url.com/test_image.jpg",
        }
        self.create_attachment()
        share_content = {
            "media": [
                media_1,
                {
                    "media": "test_exist_image.jpg",
                    "originalUrl": "https://fake-url.com/test_image.jpg",
                },
            ]
        }
        with patch.object(
            type(self.SocialAccountLinkedin),
            "_request_linkedin",
            return_value=mock_response,
        ):
            attachments = self.SocialPostAccountLinkedin._get_assets_save(share_content)
        self.assertEqual(len(attachments), 1)
        self.assertEqual(attachments[0][2]["name"], "test_image.jpg")
        self.assertEqual(attachments[0][2]["datas"], base64.b64encode(fake_content))

    @patch(PATCH_ACCOUNT_LINKEDIN.format("_request_linkedin"))
    def test_linkedin_advertising_accounts_success(self, mock_request_linkedin):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "paging": {"total": 1},
            "elements": [{"id": 123, "test": True}],
        }
        mock_request_linkedin.return_value = mock_response
        ad_account_id = self.SocialPostAccountLinkedin._linkedin_advertising_accounts()
        self.assertEqual(ad_account_id, "urn:li:sponsoredAccount:123")
        mock_request_linkedin.assert_called_once()

    @patch(PATCH_ACCOUNT_LINKEDIN.format("_request_linkedin"))
    def test_linkedin_advertising_accounts_error(self, mock_request_linkedin):
        mock_response = MagicMock()
        mock_response.status_code = 403
        mock_response.json.return_value = {"message": "Unauthorized"}
        mock_request_linkedin.return_value = mock_response
        with self.assertRaises(Exception) as context:
            self.SocialPostAccountLinkedin._linkedin_advertising_accounts()
        self.assertIn(
            "Error get advertising account in Linkedin", str(context.exception)
        )

    @patch(PATCH_ACCOUNT_LINKEDIN.format("_request_linkedin"))
    def test_action_like_post(self, mock_request):
        author_urn = "urn:li:person:abc"
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_request.return_value = mock_response
        result = self.SocialPostAccountLinkedin.action_like_post(author_urn=author_urn)
        self.assertTrue(result["success"])
        self.assertEqual(result["message"], "")

        mock_response = MagicMock()
        mock_response.status_code = 409
        mock_request.return_value = mock_response
        result = self.SocialPostAccountLinkedin.action_like_post(author_urn=author_urn)
        self.assertFalse(result["success"])
        self.assertEqual(result["message"], "You have already reacted to this post.")

        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_request.return_value = mock_response
        result = self.SocialPostAccountLinkedin.action_like_post(author_urn=author_urn)
        self.assertFalse(result["success"])
        self.assertEqual(
            result["message"], "The post does not exist or has been deleted."
        )

        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.json.return_value = {"message": "Internal error occurred."}
        mock_request.return_value = mock_response

        result = self.SocialPostAccountLinkedin.action_like_post(author_urn=author_urn)
        self.assertFalse(result["success"])
        self.assertEqual(result["message"], "Internal error occurred.")

    def test_action_like_post_failed(self):
        with patch(PATCH_POST_ACCOUNT.format("action_like_post")) as mock_like_super:
            self.SocialPostAccount.action_like_post()
            mock_like_super.assert_called_once()

    @patch(PATCH_ACCOUNT_LINKEDIN.format("_request_linkedin"))
    def test_get_comments_success(self, mock_request):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "elements": [
                {
                    "id": "comment1",
                    "message": {"text": "Great post!"},
                    "lastModified": {"actor": {"id": "actor1"}, "time": 1609459200000},
                    "content": [{"url": "http://example.com/image1.jpg"}],
                }
            ]
        }
        mock_request.return_value = mock_response
        result = self.SocialPostAccountLinkedin.get_comments()
        data = result["data"]
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["id"], "comment1")
        self.assertEqual(data[0]["text"], "Great post!")
        self.assertEqual(data[0]["actor"]["id"], "actor1")
        self.assertEqual(data[0]["images_url"], ["http://example.com/image1.jpg"])

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"elements": []}
        mock_request.return_value = mock_response
        result = self.SocialPostAccountLinkedin.get_comments()
        self.assertEqual(result["data"], [])

    @patch(PATCH_ACCOUNT_LINKEDIN.format("_request_linkedin"))
    def test_get_comments_failed(self, mock_request):
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_request.return_value = mock_response
        result = self.SocialPostAccountLinkedin.get_comments()
        self.assertFalse(result["success"])
        self.assertIn("ERROR GET COMMENTS LINKEDIN", result["message"])

    @patch(PATCH_ACCOUNT_LINKEDIN.format("_request_linkedin"))
    @patch(PATCH_ACCOUNT_LINKEDIN.format("_prepare_images_for_post"))
    def test_create_linkedin_comment_success(self, mock_prepare_images, mock_request):
        mock_prepare_images.return_value = [{"media": "asset_123"}]
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.json.return_value = {"message": "Comment created successfully"}
        mock_request.return_value = mock_response
        post_data = {
            "body": "Great post!",
            "attachment_ids": [1],
        }
        result = self.SocialPostAccountLinkedin.create_linkedin_comment(post_data)
        self.assertEqual(result["success"], True)

        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.json.return_value = {"message": "Comment created successfully"}
        mock_request.return_value = mock_response
        result = self.SocialPostAccountLinkedin.create_linkedin_comment(post_data)
        self.assertEqual(result["success"], True)

        mock_response = MagicMock()
        mock_response.status_code = 403
        mock_response.json.return_value = {"message": "Unauthorized"}
        mock_request.return_value = mock_response
        post_data.update({"attachment_ids": []})
        result = self.SocialPostAccountLinkedin.create_linkedin_comment(post_data)
        self.assertFalse(result["success"])
        self.assertIn("ERROR CREATE COMMENT LINKEDIN", result["message"])

    @patch(PATCH_ACCOUNT_LINKEDIN.format("_request_linkedin"))
    def test_delete_linkedin_comment_success(self, mock_request):
        mock_response = MagicMock()
        mock_response.status_code = 204
        mock_request.return_value = mock_response
        comment_id = "123456"
        actor_urn = "urn:li:person:abc123"
        result = self.SocialPostAccountLinkedin.delete_linkedin_comment(
            comment_id, actor_urn
        )
        self.assertEqual(result["success"], True)

        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.json.return_value = {"message": "Internal Server Error"}
        mock_request.return_value = mock_response
        result = self.SocialPostAccountLinkedin.delete_linkedin_comment(
            comment_id, actor_urn
        )
        self.assertEqual(result["success"], False)

        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.json.return_value = {"message": "Not Found"}
        mock_request.return_value = mock_response
        result = self.SocialPostAccountLinkedin.delete_linkedin_comment(
            comment_id, actor_urn
        )
        self.assertEqual(result["success"], False)

    @patch(PATCH_ACCOUNT_LINKEDIN.format("_request_linkedin"))
    def test_get_linkedin_comment_success(self, mock_request):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_request.return_value = mock_response
        result = self.SocialPostAccountLinkedin.get_linkedin_comment()
        self.assertEqual(result, True)

    @patch(PATCH_ACCOUNT_LINKEDIN.format("_request_linkedin"))
    def test_get_linkedin_comment_failed(self, mock_request):
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_request.return_value = mock_response
        result = self.SocialPostAccountLinkedin.get_linkedin_comment()
        self.assertFalse(result)
        self.assertFalse(self.SocialPostAccountLinkedin.linkedin_post_account_urn)

    def test_check_daily_budget(self):
        with self.assertRaises(ValidationError):
            self.SocialCampaignLinkedin.daily_budget = 5000
            self.SocialCampaignLinkedin2.daily_budget = 5001

    @patch(PATCH_ACCOUNT_LINKEDIN.format("_request_linkedin"))
    @patch(PATCH_POST_ACCOUNT_LINKEDIN.format("_action_campaign"))
    def test_action_campaign_post(self, mock_action_campaign, mock_request_linkedin):
        mock_action_campaign.return_value = "urn:li:sponsoredCampaign:001"
        mock_request_linkedin.side_effect = [
            MagicMock(
                status_code=201, headers={"Location": "/adCampaignGroupsV2/123456"}
            ),
        ]
        res = self.SocialPostAccountCampaignLinkedin._action_campaign_post(
            self.SocialPostAccountCampaignLinkedin.id
        )
        self.assertEqual(res, "123456")

        mock_request_linkedin.side_effect = [
            MagicMock(
                status_code=404, headers={"Location": "/adCampaignGroupsV2/123456"}
            ),
        ]
        with self.assertRaises(ValidationError):
            self.SocialPostAccountCampaignLinkedin._action_campaign_post(
                self.SocialPostAccountCampaignLinkedin.id
            )

        mock_action_campaign.return_value = False
        with self.assertRaises(ValidationError):
            self.SocialPostAccountCampaignLinkedin._action_campaign_post(
                self.SocialPostAccountCampaignLinkedin.id
            )

        self.assertEqual(mock_action_campaign.call_count, 3)

    def test_action_like_comment(self):
        result = self.SocialPostAccountLinkedin.action_like_comment()
        self.assertEqual(result, {"success": False, "message": ""})

    @patch(PATCH_POST_ACCOUNT_LINKEDIN.format("create_linkedin_comment"))
    @patch(PATCH_ACCOUNT_LINKEDIN.format("_request_linkedin"))
    def test_create_comment(self, mock_request_linkedin, mock_create_linkedin_comment):
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_request_linkedin.return_value = mock_response
        result = self.SocialPostAccountLinkedin.create_comment(
            {"body": "Test comment", "attachment_ids": [1]}
        )
        self.assertTrue(result["success"])
        mock_create_linkedin_comment.assert_called_once()

    def test_compute_message_info(self):
        post_message_info = self.SocialPost.create(
            {
                "message": self.test_message,
                "account_ids": [Command.set(self.SocialAccountLinkedin.ids)],
                "image_ids": [Command.set([self.create_attachment().id])],
                "video_ids": [
                    Command.set([self.create_attachment("test_video.mp4").id])
                ],
            }
        )
        self.assertTrue(post_message_info.message_info)
        self.assertIn(
            "You have selected images and videos for this post",
            post_message_info.message_info,
        )

        post = self.SocialPost.create(
            {
                "message": self.test_message,
                "account_ids": [Command.set(self.SocialAccountLinkedin.ids)],
                "image_ids": [Command.set([self.create_attachment().id])],
            }
        )
        self.assertFalse(post.message_info)

    def test_post_schedule(self):
        post_hide = self.SocialPost.create(
            {
                "message": self.test_message,
                "send_post": "schedule",
                "account_ids": [Command.set(self.SocialAccountLinkedin.ids)],
            }
        )
        self.assertEqual(post_hide.state, "planned")
        self.assertTrue(post_hide.hide_post)
        post_hide.action_draft()
        self.assertEqual(post_hide.state, "draft")
        self.assertFalse(post_hide.hide_post)
        post_hide.send_post = "schedule"
        post_hide.action_cancel()
        self.assertEqual(post_hide.state, "cancelled")

    @patch(PATCH_ACCOUNT_LINKEDIN.format("_request_linkedin"))
    def test_delete_post_account(self, mock_request_linkedin):
        mock_response = MagicMock()
        mock_response.status_code = 204
        mock_request_linkedin.return_value = mock_response
        self.SocialPostAccountLinkedin._delete_post_account()

        mock_failed_response = MagicMock()
        mock_failed_response.status_code = 404
        mock_request_linkedin.return_value = mock_failed_response
        with self.assertRaises(ValidationError):
            self.SocialPostAccountLinkedin._delete_post_account()
        self.assertEqual(mock_request_linkedin.call_count, 2)

    def get_patch_advertising(self, advertising=False):
        return patch.object(
            type(self.SocialPostAccountLinkedin),
            "_linkedin_advertising_accounts",
            autospec=True,
            return_value=advertising,
        )

    def test_not_action_campaign_group(self):
        patch_advertising = self.get_patch_advertising()
        with patch_advertising as mock_advertising_accounts:
            self.SocialPostAccountLinkedin._action_campaign_group()
            mock_advertising_accounts.assert_called_once()

    def test_action_exist_campaign_group(self):
        patch_advertising = self.get_patch_advertising(True)
        fake_campaign_group = MagicMock()
        fake_campaign_group.status_code = 200
        patch_request_linkedin = self.get_patch_exceptions_linkedin(fake_campaign_group)
        with (
            patch_advertising as mock_advertising_accounts,
            patch_request_linkedin as mock_request_linkedin,
        ):
            res = self.SocialPostAccountCampaignLinkedin._action_campaign_group()
            self.assertEqual(
                self.SocialPostCampaignLinkedin.campaign_id.campaign_group_id.linkedin_urn,
                res,
            )
            mock_request_linkedin.assert_called_once()
            mock_advertising_accounts.assert_called_once()

    def test_create_new_campaign_group(self):
        patch_advertising = self.get_patch_advertising(True)
        patch_request_linkedin = self.get_patch_exceptions_linkedin(
            side_effect=[
                MagicMock(status_code=404),
                MagicMock(
                    status_code=201, headers={"Location": "/adCampaignGroupsV2/456"}
                ),
            ]
        )
        fake_timestamps = (111111, 222222)
        with (
            patch(
                PATCH_SOCIAL_BASE_UTILS.format("_generate_timestamps"),
                autospec=True,
                return_value=fake_timestamps,
            ),
            patch_request_linkedin as mock_request,
            patch_advertising as mock_ad_accounts,
        ):
            urn = self.SocialPostAccountCampaignLinkedin._action_campaign_group()
            self.assertEqual(urn, "urn:li:sponsoredCampaignGroup:456")
            self.assertEqual(
                self.SocialCampaignGroupLinkedin.linkedin_urn,
                "urn:li:sponsoredCampaignGroup:456",
            )
            self.assertEqual(mock_request.call_count, 2)
            mock_ad_accounts.assert_called_once()

    def test_campaign_group_error(self):
        patch_advertising = self.get_patch_advertising(True)
        patch_request_linkedin = self.get_patch_exceptions_linkedin(
            side_effect=[
                MagicMock(status_code=404),
                MagicMock(status_code=400, headers={"error": "Invalid request"}),
            ]
        )
        with (
            patch_advertising as mock_ad_accounts,
            patch_request_linkedin as mock_request_linkedin,
        ):
            with self.assertRaises(ValidationError) as e:
                self.SocialPostAccountCampaignLinkedin._action_campaign_group()
            self.assertIn("Error creating group campaign in Linkedin", str(e.exception))
            mock_ad_accounts.assert_called_once()
            self.assertEqual(mock_request_linkedin.call_count, 2)

    def test_not_create_campaign_group_error(self):
        patch_advertising = self.get_patch_advertising(True)
        patch_request_linkedin = self.get_patch_exceptions_linkedin(
            side_effect=[MagicMock(status_code=400)]
        )
        with (
            patch_advertising as mock_ad_accounts,
            patch_request_linkedin as mock_request_linkedin,
        ):
            with self.assertRaises(ValidationError) as e:
                self.SocialPostAccountCampaignLinkedin._action_campaign_group()
            self.assertIn("Error creating group campaign in Linkedin", str(e.exception))
            mock_ad_accounts.assert_called_once()
            mock_request_linkedin.assert_called_once()

    def get_patch_campaign_group(self, campaign_group=False):
        return patch.object(
            type(self.SocialPostAccountLinkedin),
            "_action_campaign_group",
            autospec=True,
            return_value=campaign_group,
        )

    def test_not_action_campaign(self):
        patch_campaign_group = self.get_patch_campaign_group()
        with patch_campaign_group as mock_campaign_group:
            self.SocialPostAccountLinkedin._action_campaign()
            mock_campaign_group.assert_called_once()

    def test_action_exist_campaign(self):
        patch_campaign_group = self.get_patch_campaign_group(True)
        fake_campaign = MagicMock()
        fake_campaign.status_code = 200
        patch_request_linkedin = self.get_patch_exceptions_linkedin(fake_campaign)
        with (
            patch_campaign_group as mock_campaign_group,
            patch_request_linkedin as mock_request_linkedin,
        ):
            res = self.SocialPostAccountCampaignLinkedin._action_campaign()
            self.assertEqual(
                self.SocialPostCampaignLinkedin.campaign_id.linkedin_urn,
                res,
            )
            mock_request_linkedin.assert_called_once()
            mock_campaign_group.assert_called_once()

    def test_create_new_campaign(self):
        patch_campaign_group = self.get_patch_campaign_group(True)
        patch_advertising = self.get_patch_advertising("urn:li:sponsoredAccount:999")
        patch_request_linkedin = self.get_patch_exceptions_linkedin(
            side_effect=[
                MagicMock(status_code=404),
                MagicMock(status_code=201, headers={"Location": "/adCampaignV2/456"}),
            ]
        )
        fake_timestamps = (111111, 222222)
        with (
            patch(
                PATCH_SOCIAL_BASE_UTILS.format("_generate_timestamps"),
                autospec=True,
                return_value=fake_timestamps,
            ),
            patch_request_linkedin as mock_request,
            patch_campaign_group as mock_campaign_group,
            patch_advertising as mock_ad_accounts,
        ):
            urn = self.SocialPostAccountCampaignLinkedin._action_campaign()
            self.assertEqual(urn, "urn:li:sponsoredCampaign:456")
            self.assertEqual(
                self.SocialCampaignLinkedin.linkedin_urn,
                "urn:li:sponsoredCampaign:456",
            )
            self.assertEqual(mock_request.call_count, 2)
            mock_campaign_group.assert_called_once()
            mock_ad_accounts.assert_called_once()

    def test_create_new_campaign_error(self):
        patch_campaign_group = self.get_patch_campaign_group(True)
        patch_advertising = self.get_patch_advertising("urn:li:sponsoredAccount:999")
        patch_request_linkedin = self.get_patch_exceptions_linkedin(
            side_effect=[
                MagicMock(status_code=404),
                MagicMock(status_code=400, headers={"error": "Bad request"}),
            ]
        )
        with (
            patch_request_linkedin as mock_request,
            patch_campaign_group as mock_campaign_group,
            patch_advertising as mock_ad_accounts,
        ):
            with self.assertRaises(ValidationError) as ctx:
                self.SocialPostAccountCampaignLinkedin._action_campaign()
            self.assertIn("Error creating campaign in Linkedin", str(ctx.exception))
            self.assertEqual(mock_request.call_count, 2)
            mock_campaign_group.assert_called_once()
            mock_ad_accounts.assert_called_once()

    def test_action_post(self):
        self.SocialPostAccountLinkedin.write({"state": "ready"})
        post_account_id = "122809890045"
        expected_urn = f"urn:li:share:{post_account_id}"
        fake_response = MagicMock(return_value=[{"share_content": self.image_base64}])
        with (
            patch.object(
                type(self.SocialPostLinkedin),
                "filter_by_media_types",
                autospec=True,
                return_value=self.SocialPostAccountLinkedin,
            ) as mock_filter_by_media_types,
            patch.object(
                type(self.SocialPostAccountLinkedin.account_id),
                "create_restclient_linkedin",
                autospec=True,
                return_value=post_account_id,
            ) as mock_create_restclient_linkedin,
            patch.object(
                type(self.SocialPostAccountLinkedin.account_id),
                "_get_posts",
                autospec=True,
                return_value=fake_response,
            ) as mock_get_posts,
            patch.object(
                type(self.SocialPostAccountLinkedin),
                "_get_assets_save",
                autospec=True,
                return_value=[12],
            ) as mock_get_assets_save,
        ):
            self.SocialPostAccountLinkedin._action_post(self.SocialPostLinkedin)
            self.assertEqual(
                self.SocialPostAccountLinkedin.linkedin_post_account_urn,
                expected_urn,
            )
            self.assertEqual(self.SocialPostAccountLinkedin.state, "posted")
            self.assertIn(
                expected_urn,
                self.SocialPostAccountLinkedin.post_account_url,
            )
            mock_filter_by_media_types.assert_called_once()
            mock_create_restclient_linkedin.assert_called_once()
            mock_get_posts.assert_called_once()
            mock_get_assets_save.assert_called_once()

    def test_action_post_failed(self):
        self.SocialPostAccountLinkedin.write({"state": "ready"})
        with (
            patch.object(
                type(self.SocialPostLinkedin),
                "filter_by_media_types",
                autospec=True,
                return_value=self.SocialPostAccountLinkedin,
            ) as mock_filter_by_media_types,
            patch.object(
                type(self.SocialPostAccountLinkedin.account_id),
                "create_restclient_linkedin",
                autospec=True,
                return_value=False,
            ) as mock_create_restclient_linkedin,
        ):
            self.SocialPostAccountLinkedin._action_post(self.SocialPostLinkedin)
            self.assertEqual(self.SocialPostAccountLinkedin.state, "failed")
            mock_filter_by_media_types.assert_called_once()
            mock_create_restclient_linkedin.assert_called_once()