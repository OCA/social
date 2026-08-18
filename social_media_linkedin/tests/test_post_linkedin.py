# Copyright 2025 Binhex <https://www.binhex.cloud>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import base64
from unittest.mock import MagicMock, patch

from odoo import Command
from odoo.exceptions import UserError, ValidationError
from odoo.tools import mute_logger

from odoo.addons.social_media_base.tests.test_social_common import (
    PATCH_POST_ACCOUNT,
    PATCH_SOCIAL_BASE_UTILS,
)
from odoo.addons.social_media_linkedin.tests.test_common_linkedin import (
    PATCH_ACCOUNT_LINKEDIN,
    PATCH_POST_ACCOUNT_LINKEDIN,
    TestSocialCommonLinkedin,
)

LOGGER_POST_ACCOUNT_LINKEDIN = (
    "odoo.addons.social_media_linkedin.models.social_post_account"
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
                "res_model": "social.post.account",
                "res_id": self.SocialPostAccountLinkedin.id,
            }
        )

    @patch("odoo.addons.social_media_linkedin.models.social_account.requests.get")
    def test_get_assets_save(self, mock_get):
        """Only the images that are not stored yet are downloaded."""
        fake_content = b"fake image data"
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = fake_content
        mock_get.return_value = mock_response
        self.create_attachment(attach_name="urn:li:image:exists")
        content = {
            "multiImage": {
                "images": [
                    {"id": "urn:li:image:new"},
                    {"id": "urn:li:image:exists"},
                ]
            }
        }
        images_response = MagicMock()
        images_response.status_code = 200
        images_response.json.return_value = {
            "results": {"urn:li:image:new": {"downloadUrl": "https://fake-url/new.jpg"}}
        }
        with patch.object(
            type(self.SocialAccountLinkedin),
            "_request_linkedin",
            return_value=images_response,
        ) as mock_request_linkedin:
            attachments = self.SocialPostAccountLinkedin._get_assets_save(content)
        self.assertEqual(len(attachments), 1)
        self.assertEqual(attachments[0][2]["name"], "urn:li:image:new")
        self.assertEqual(attachments[0][2]["datas"], base64.b64encode(fake_content))
        self.assertEqual(
            mock_request_linkedin.call_args.kwargs["params_values"]["ids"],
            ["urn:li:image:new"],
        )

    def test_get_assets_save_single_image(self):
        """The image of a post with a single media is resolved as well."""
        content = {"media": {"id": "urn:li:image:single"}}
        with patch.object(
            type(self.SocialAccountLinkedin),
            "_get_linkedin_images_download_url",
            return_value={},
        ) as mock_download_url:
            self.assertEqual(
                self.SocialPostAccountLinkedin._get_assets_save(content), []
            )
        mock_download_url.assert_called_once_with(["urn:li:image:single"])

    def test_get_assets_save_without_images(self):
        """A post with a video or without media does not ask for any image."""
        with patch.object(
            type(self.SocialAccountLinkedin),
            "_get_linkedin_images_download_url",
        ) as mock_download_url:
            self.assertEqual(
                self.SocialPostAccountLinkedin._get_assets_save(
                    {"media": {"id": "urn:li:video:1"}}
                ),
                [],
            )
            self.assertEqual(self.SocialPostAccountLinkedin._get_assets_save({}), [])
        mock_download_url.assert_not_called()

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
        mock_response.text = '{"message": "Internal error occurred."}'
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

    @mute_logger(LOGGER_POST_ACCOUNT_LINKEDIN)
    @patch(PATCH_ACCOUNT_LINKEDIN.format("_request_linkedin"))
    def test_get_comments_failed(self, mock_request):
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_request.return_value = mock_response
        result = self.SocialPostAccountLinkedin.get_comments()
        self.assertFalse(result["success"])
        self.assertIn("ERROR GET COMMENTS LINKEDIN", result["message"])

    @mute_logger(LOGGER_POST_ACCOUNT_LINKEDIN)
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
        self.assertFalse(self.SocialPostAccountLinkedin.remote_ref)

    def test_validate_publish_linkedin_video_objective(self):
        """LinkedIn requires an objective to create a video campaign."""
        campaign = self.SocialCampaignLinkedin
        campaign.write(
            {
                "linkedin_format": "SINGLE_VIDEO",
                "linkedin_objective": False,
                "unit_cost": 2,
                "daily_budget": 20,
                "account_id": self.SocialAccountLinkedin.id,
            }
        )
        with self.assertRaises(UserError) as context:
            campaign._validate_publish_linkedin()
        self.assertIn("requires an objective", str(context.exception))

        campaign.linkedin_objective = "VIDEO_VIEW"
        campaign._validate_publish_linkedin()

    def test_linkedin_create_campaign_sends_format(self):
        """The ad format travels to LinkedIn, which fixes it on creation."""
        campaign = self.SocialCampaignLinkedin
        campaign.linkedin_format = "SINGLE_VIDEO"
        campaign.linkedin_objective = "VIDEO_VIEW"
        response = MagicMock(status_code=201)
        response.headers = {"Location": "/adCampaignsV2/321"}
        patch_request_linkedin = self.get_patch_exceptions_linkedin(response)
        with patch_request_linkedin as mock_request_linkedin:
            res = campaign._linkedin_create_campaign(
                self.SocialAccountLinkedin,
                "urn:li:sponsoredAccount:999",
                "urn:li:sponsoredCampaignGroup:456",
            )
        self.assertEqual(res, "urn:li:sponsoredCampaign:321")
        json_data = mock_request_linkedin.call_args.kwargs["json_data"]
        self.assertEqual(json_data["format"], "SINGLE_VIDEO")
        self.assertEqual(json_data["objectiveType"], "VIDEO_VIEW")

    def test_check_linkedin_campaign_format(self):
        """The post and its campaign must share the LinkedIn ad format."""
        post_account = self.SocialPostAccountCampaignLinkedin
        campaign = post_account.post_id.campaign_id
        # A post without a video fits the standard format.
        campaign.linkedin_format = "STANDARD_UPDATE"
        post_account._check_linkedin_campaign_format()

        post_account.post_id.video_ids = [
            Command.set([self.create_attachment("test_video.mp4").id])
        ]
        with self.assertRaises(UserError) as context:
            post_account._check_linkedin_campaign_format()
        self.assertIn("'Single video' format", str(context.exception))

        # The video campaign accepts it, but then refuses a post without one.
        campaign.linkedin_format = "SINGLE_VIDEO"
        post_account._check_linkedin_campaign_format()
        post_account.post_id.video_ids = [Command.clear()]
        with self.assertRaises(UserError) as context:
            post_account._check_linkedin_campaign_format()
        self.assertIn("only accepts posts containing a video", str(context.exception))

    def test_check_linkedin_campaign_format_multi_image(self):
        """LinkedIn does not sponsor a post carrying several images."""
        post_account = self.SocialPostAccountCampaignLinkedin
        post_account.post_id.campaign_id.linkedin_format = "STANDARD_UPDATE"
        post_account.post_id.image_ids = [
            Command.set(
                [
                    self.create_attachment("image_1.png").id,
                    self.create_attachment("image_2.png").id,
                ]
            )
        ]
        with self.assertRaises(UserError) as context:
            post_account._check_linkedin_campaign_format()
        self.assertIn("several images", str(context.exception))

        # A single image is sponsored without any complaint.
        post_account.post_id.image_ids = [
            Command.set([self.create_attachment("image_1.png").id])
        ]
        post_account._check_linkedin_campaign_format()

    def test_check_daily_budget(self):
        with self.assertRaises(ValidationError):
            self.SocialCampaignLinkedin.daily_budget = 5000
            self.SocialCampaignLinkedin2.daily_budget = 5001

    @patch(PATCH_ACCOUNT_LINKEDIN.format("_get_linkedin_ad_account_id"))
    @patch(PATCH_ACCOUNT_LINKEDIN.format("_request_linkedin"))
    def test_action_campaign_post(self, mock_request_linkedin, mock_get_ad_account_id):
        creative_urn = "urn:li:sponsoredCreative:123456"
        mock_get_ad_account_id.return_value = "999"
        campaign = self.SocialPostCampaignLinkedin.campaign_id
        campaign.remote_ref = "urn:li:sponsoredCampaign:001"
        mock_request_linkedin.side_effect = [
            MagicMock(status_code=201, headers={"x-restli-id": creative_urn}),
        ]
        res = self.SocialPostAccountCampaignLinkedin._action_campaign_post(
            self.SocialPostAccountCampaignLinkedin.id
        )
        self.assertEqual(res, creative_urn)
        # The creative is created on the Creatives API of the ad account.
        self.assertEqual(
            mock_request_linkedin.call_args.kwargs["endpoint"],
            "/adAccounts/999/creatives",
        )

        mock_request_linkedin.side_effect = [
            MagicMock(status_code=404, headers={"x-restli-id": creative_urn}),
        ]
        with self.assertRaises(UserError):
            self.SocialPostAccountCampaignLinkedin._action_campaign_post(
                self.SocialPostAccountCampaignLinkedin.id
            )

        campaign.remote_ref = False
        with self.assertRaises(UserError) as context:
            self.SocialPostAccountCampaignLinkedin._action_campaign_post(
                self.SocialPostAccountCampaignLinkedin.id
            )
        self.assertIn("has not been created on LinkedIn", str(context.exception))
        self.assertEqual(mock_request_linkedin.call_count, 2)

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

    def test_compute_message_info_recomputed_on_media_change(self):
        post = self.SocialPost.create(
            {
                "message": self.test_message,
                "account_ids": [Command.set(self.SocialAccountLinkedin.ids)],
                "image_ids": [Command.set([self.create_attachment().id])],
            }
        )
        self.assertFalse(post.message_info)

        post.video_ids = [Command.set([self.create_attachment("test_video.mp4").id])]
        self.assertIn(
            "You have selected images and videos for this post",
            post.message_info,
        )

        post.image_ids = [Command.clear()]
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
        with self.assertRaises(UserError):
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
                self.SocialPostCampaignLinkedin.campaign_id.campaign_group_id.remote_ref,
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
                self.SocialCampaignGroupLinkedin.remote_ref,
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
            with self.assertRaises(UserError) as e:
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
            with self.assertRaises(UserError) as e:
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
                self.SocialPostCampaignLinkedin.campaign_id.remote_ref,
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
                self.SocialCampaignLinkedin.remote_ref,
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
            with self.assertRaises(UserError) as ctx:
                self.SocialPostAccountCampaignLinkedin._action_campaign()
            self.assertIn("Error creating campaign in Linkedin", str(ctx.exception))
            self.assertEqual(mock_request.call_count, 2)
            mock_campaign_group.assert_called_once()
            mock_ad_accounts.assert_called_once()

    def test_action_post(self):
        self.SocialPostAccountLinkedin.write({"state": "ready"})
        post_account_urn = "urn:li:share:122809890045"
        attachment = self.env["ir.attachment"].create(
            {"name": "fake-asset.png", "datas": self.image_base64}
        )
        fake_response = [
            {
                "id": post_account_urn,
                "content": {"media": {"id": "urn:li:image:1"}},
            }
        ]
        with (
            patch.object(
                type(self.SocialPostLinkedin),
                "filter_by_media_types",
                autospec=True,
                return_value=self.SocialPostAccountLinkedin,
            ) as mock_filter_by_media_types,
            patch.object(
                type(self.SocialPostAccountLinkedin.account_id),
                "_linkedin_create_post",
                autospec=True,
                return_value=post_account_urn,
            ) as mock_linkedin_create_post,
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
                return_value=[attachment.id],
            ) as mock_get_assets_save,
        ):
            self.SocialPostAccountLinkedin._action_post(self.SocialPostLinkedin)
            self.assertEqual(
                self.SocialPostAccountLinkedin.remote_ref,
                post_account_urn,
            )
            self.assertEqual(self.SocialPostAccountLinkedin.state, "posted")
            self.assertFalse(self.SocialPostAccountLinkedin.has_video)
            self.assertEqual(
                self.SocialPostAccountLinkedin.post_account_url,
                f"https://www.linkedin.com/feed/update/{post_account_urn}",
            )
            mock_filter_by_media_types.assert_called_once()
            mock_linkedin_create_post.assert_called_once()
            mock_get_posts.assert_called_once()
            mock_get_assets_save.assert_called_once()

    def test_action_post_video_sets_has_video(self):
        self.SocialPostAccountLinkedin.write({"state": "ready"})
        self.SocialPostLinkedin.write(
            {"video_ids": [Command.set([self.create_attachment("test_video.mp4").id])]}
        )
        post_account_urn = "urn:li:ugcPost:122809890045"
        fake_response = [
            {
                "id": post_account_urn,
                "content": {"media": {"id": "urn:li:image:1"}},
            }
        ]
        with (
            patch.object(
                type(self.SocialPostLinkedin),
                "filter_by_media_types",
                autospec=True,
                return_value=self.SocialPostAccountLinkedin,
            ),
            patch.object(
                type(self.SocialPostAccountLinkedin.account_id),
                "_linkedin_create_post",
                autospec=True,
                return_value=post_account_urn,
            ),
            patch.object(
                type(self.SocialPostAccountLinkedin.account_id),
                "_get_posts",
                autospec=True,
                return_value=fake_response,
            ),
            patch.object(
                type(self.SocialPostAccountLinkedin),
                "_get_assets_save",
                autospec=True,
                return_value=[],
            ),
        ):
            self.SocialPostAccountLinkedin._action_post(self.SocialPostLinkedin)
        self.assertEqual(self.SocialPostAccountLinkedin.state, "posted")
        self.assertTrue(self.SocialPostAccountLinkedin.has_video)

    def _set_linkedin_campaign(self, remote_ref=False):
        group = self.env["utm.group.campaign"].create({"name": "Test Group"})
        campaign = self.env["utm.campaign"].create(
            {
                "name": "Test Campaign",
                "campaign_group_id": group.id,
                "media_id": self.media_linkedin_id.id,
                "account_id": self.SocialAccountLinkedin.id,
                "remote_ref": remote_ref,
            }
        )
        self.SocialPostLinkedin.write({"campaign_id": campaign.id})
        return campaign

    def test_action_post_campaign_precheck_blocks_publish(self):
        self.SocialPostAccountLinkedin.write({"state": "ready"})
        self._set_linkedin_campaign()
        with (
            patch.object(
                type(self.SocialPostLinkedin),
                "filter_by_media_types",
                autospec=True,
                return_value=self.SocialPostAccountLinkedin,
            ),
            patch.object(
                type(self.SocialPostAccountLinkedin),
                "_linkedin_advertising_accounts",
                autospec=True,
                side_effect=UserError("Ads access denied"),
            ),
            patch.object(
                type(self.SocialPostAccountLinkedin.account_id),
                "_linkedin_create_post",
                autospec=True,
            ) as mock_linkedin_create_post,
        ):
            with self.assertRaises(UserError):
                self.SocialPostAccountLinkedin._action_post(self.SocialPostLinkedin)
            mock_linkedin_create_post.assert_not_called()
        self.assertEqual(self.SocialPostAccountLinkedin.state, "ready")

    @mute_logger(LOGGER_POST_ACCOUNT_LINKEDIN)
    def test_action_post_campaign_failure_keeps_posted(self):
        self.SocialPostAccountLinkedin.write({"state": "ready"})
        self._set_linkedin_campaign(remote_ref="urn:li:sponsoredCampaign:001")
        post_account_urn = "urn:li:share:122809890045"
        fake_response = [
            {
                "id": post_account_urn,
                "content": {"media": {"id": "urn:li:image:1"}},
            }
        ]
        with (
            patch.object(
                type(self.SocialPostLinkedin),
                "filter_by_media_types",
                autospec=True,
                return_value=self.SocialPostAccountLinkedin,
            ),
            patch.object(
                type(self.SocialPostAccountLinkedin),
                "_linkedin_advertising_accounts",
                autospec=True,
                return_value="urn:li:sponsoredAccount:123",
            ),
            patch.object(
                type(self.SocialPostAccountLinkedin.account_id),
                "_linkedin_create_post",
                autospec=True,
                return_value=post_account_urn,
            ),
            patch.object(
                type(self.SocialPostAccountLinkedin.account_id),
                "_get_posts",
                autospec=True,
                return_value=fake_response,
            ),
            patch.object(
                type(self.SocialPostAccountLinkedin),
                "_get_assets_save",
                autospec=True,
                return_value=[],
            ),
            patch.object(
                type(self.SocialPostAccountLinkedin),
                "_action_campaign_post",
                autospec=True,
                side_effect=UserError("Creative error"),
            ),
        ):
            self.SocialPostAccountLinkedin._action_post(self.SocialPostLinkedin)
        self.assertEqual(self.SocialPostAccountLinkedin.state, "posted")
        self.assertEqual(
            self.SocialPostAccountLinkedin.remote_ref,
            post_account_urn,
        )
        self.assertFalse(self.SocialPostAccountLinkedin.creative_urn)

    def test_action_publish_linkedin_validation(self):
        campaign = self._set_linkedin_campaign()
        with self.assertRaises(UserError) as context:
            campaign.action_publish_linkedin()
        self.assertIn("total budget must be positive", str(context.exception))
        self.assertIn("unit cost must be positive", str(context.exception))
        self.assertIn("daily budget must be positive", str(context.exception))

    @patch(PATCH_ACCOUNT_LINKEDIN.format("_request_linkedin"))
    @patch(PATCH_ACCOUNT_LINKEDIN.format("_get_linkedin_advertising_account"))
    def test_action_publish_linkedin(
        self, mock_advertising_account, mock_request_linkedin
    ):
        campaign = self._set_linkedin_campaign()
        currency = self.env.ref("base.USD")
        campaign.campaign_group_id.write(
            {"total_budget": 100, "currency_id": currency.id}
        )
        campaign.write({"unit_cost": 1, "daily_budget": 10})
        mock_advertising_account.return_value = "urn:li:sponsoredAccount:999"
        mock_request_linkedin.side_effect = [
            MagicMock(status_code=201, headers={"Location": "/adCampaignGroupsV2/45"}),
            MagicMock(status_code=201, headers={"Location": "/adCampaignsV2/67"}),
        ]
        campaign.action_publish_linkedin()
        self.assertEqual(
            campaign.campaign_group_id.remote_ref,
            "urn:li:sponsoredCampaignGroup:45",
        )
        self.assertEqual(campaign.remote_ref, "urn:li:sponsoredCampaign:67")
        for call in mock_request_linkedin.call_args_list:
            self.assertEqual(call.kwargs["json_data"]["status"], "DRAFT")

    def test_allow_campaign_ids_filters_unpublished(self):
        campaign = self._set_linkedin_campaign()
        self.SocialPostLinkedin.invalidate_recordset()
        self.assertNotIn(campaign, self.SocialPostLinkedin.allow_campaign_ids)
        campaign.remote_ref = "urn:li:sponsoredCampaign:001"
        self.SocialPostLinkedin.invalidate_recordset()
        self.assertIn(campaign, self.SocialPostLinkedin.allow_campaign_ids)

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
                "_linkedin_create_post",
                autospec=True,
                return_value=False,
            ) as mock_linkedin_create_post,
        ):
            self.SocialPostAccountLinkedin._action_post(self.SocialPostLinkedin)
            self.assertEqual(self.SocialPostAccountLinkedin.state, "failed")
            mock_filter_by_media_types.assert_called_once()
            mock_linkedin_create_post.assert_called_once()
