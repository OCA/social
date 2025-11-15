# Copyright 2025 Binhex <https://www.binhex.cloud>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).


from datetime import datetime, timedelta
from unittest.mock import MagicMock, Mock, patch

from linkedin_api.clients.restli.client import RestliClient

from odoo.exceptions import ValidationError

from odoo.addons.social_media_base.tests.test_social_common import (
    PATCH_ACCOUNT,
    PATCH_SOCIAL_BASE_MIXIN,
    PATCH_WIZARD_ACCOUNT,
)
from odoo.addons.social_media_linkedin.tests.test_common_linkedin import (
    PATCH_ACCOUNT_LINKEDIN,
    PATCH_WIZARD_ACCOUNT_LINKEDIN,
    TestSocialCommonLinkedin,
)


class LinkedinMockMixin:
    def _mock_linkedin(self, return_value, account, attribute="_request_linkedin"):
        return patch.object(type(account), attribute, return_value=return_value)


class TestSocialLinkedin(LinkedinMockMixin, TestSocialCommonLinkedin):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.video_mock = type("Video", (), {"datas": cls.video_data})()
        cls.mediaAsset = "urn:li:digitalmediaAsset:{}"
        cls.mediaImage = "urn:li:digitalmediaImage:{}"

    def test_prepare_url_upload_asset_image(self):
        fake_response = {
            "value": {
                "asset": self.mediaAsset.format("C123"),
                "uploadMechanism": {
                    "com.linkedin.digitalmedia.uploading.MediaUploadHttpRequest": {
                        "uploadUrl": "https://fake.upload.url/image"
                    }
                },
            }
        }

        patch_request_linkedin = self.get_patch_exceptions_linkedin(fake_response)
        with patch_request_linkedin as mock_request:
            asset, upload_url = self.SocialAccountLinkedin._prepare_url_upload_asset(
                feedshare="image"
            )

            self.assertEqual(asset, self.mediaAsset.format("C123"))
            self.assertEqual(upload_url, "https://fake.upload.url/image")

            mock_request.assert_called_once()
            args, kwargs = mock_request.call_args
            self.assertEqual(kwargs["method"], "POST")
            self.assertIn(
                "feedshare-image",
                kwargs["json_data"]["registerUploadRequest"]["recipes"][0],
            )

    def test_prepare_url_upload_image(self):
        fake_response = {
            "value": {
                "image": self.mediaImage.format("C123456"),
                "uploadUrl": "https://fake.upload.url/image",
            }
        }

        patch_request_linkedin = self.get_patch_exceptions_linkedin(fake_response)

        with patch_request_linkedin as mock_request:
            image, upload_url = self.SocialAccountLinkedin._prepare_url_upload_image()

            self.assertEqual(image, self.mediaImage.format("C123456"))
            self.assertEqual(upload_url, "https://fake.upload.url/image")

            mock_request.assert_called_once()

    def test_prepare_images_videos_for_post_success(self):
        mock_upload_asset_image = (
            self.mediaAsset.format("XYZ"),
            "https://fake.upload/asset/image",
        )
        mock_upload_asset_video = (
            self.mediaAsset.format("VID123"),
            "https://fake.upload/asset/video",
        )
        mock_response = self.generate_magic_mock(
            **{
                "status_code": 201,
            }
        )

        mock_upload_image = patch.object(
            type(self.SocialAccountLinkedin),
            "_prepare_url_upload_asset",
            return_value=mock_upload_asset_image,
        )

        patch_request_linkedin = self.get_patch_exceptions_linkedin(mock_response)

        with mock_upload_image, patch_request_linkedin:
            images = self.SocialAccountLinkedin._prepare_images_for_post(
                image_ids=[self.image_base64]
            )
            self.assertEqual(len(images), 1)
            self.assertEqual(images[0], self.mediaAsset.format("XYZ"))

        mock_upload_video = patch.object(
            type(self.SocialAccountLinkedin),
            "_prepare_url_upload_asset",
            return_value=mock_upload_asset_video,
        )

        with mock_upload_video, patch_request_linkedin:
            videos = self.SocialAccountLinkedin._prepare_videos_for_post(
                video_ids=[self.video_mock]
            )
            self.assertEqual(len(videos), 1)
            self.assertEqual(videos[0], self.mediaAsset.format("VID123"))

    def test_get_posts(self):
        mock_response = self.generate_magic_mock(
            **{
                "status_code": 200,
                "json_return_value": {
                    "elements": [
                        {
                            "id": "123",
                            "specificContent": {
                                "com.linkedin.ugc.ShareContent": {"text": "Post 1"}
                            },
                        },
                        {
                            "id": "456",
                            "specificContent": {
                                "com.linkedin.ugc.ShareContent": {"text": "Post 2"}
                            },
                        },
                    ]
                },
            }
        )

        patch_request_linkedin = self.get_patch_exceptions_linkedin(mock_response)

        with patch_request_linkedin as mock_request_linkedin:
            posts = self.SocialAccountLinkedin._get_posts()
            self.assertEqual(len(posts), 2)
            self.assertEqual(posts[0]["id"], "123")
            self.assertEqual(posts[1]["id"], "456")
            self.assertEqual(posts[0]["share_content"]["text"], "Post 1")
            self.assertEqual(posts[1]["share_content"]["text"], "Post 2")
            mock_request_linkedin.assert_called_once()

        mock_response_failed = self.generate_magic_mock(**{"status_code": 400})
        patch_request_linkedin_failed = self.get_patch_exceptions_linkedin(
            mock_response_failed
        )
        with patch_request_linkedin_failed as mock_request_linkedin_failed:
            with self.assertRaises(ValidationError):
                self.SocialAccountLinkedin._get_posts()
            mock_request_linkedin_failed.assert_called_once()

    def test_get_chart_account_statistics(self):
        patch_get_default_filter_date = self.generate_patch(
            **{
                "type_object": True,
                "model_patch": self.SocialAccountLinkedin,
                "method_patch": "_get_default_filter_date",
                "return_value": (
                    "2025-01-01T00:00:00",
                    "2025-01-07T23:59:59",
                ),
            }
        )
        patch_get_entity_statistics = self.generate_patch(
            **{
                "type_object": True,
                "model_patch": self.SocialAccountLinkedin,
                "method_patch": "get_entity_statistics",
                "return_value": {
                    "urn:li:ugcPost:0119424": (100, 30, 50, 0, 0, 0),
                    "urn:li:ugcPost:0115624": (200, 70, 100, 0, 0, 0),
                },
            }
        )

        with patch_get_default_filter_date, patch_get_entity_statistics:
            result = self.SocialAccountLinkedin._get_chart_account_statistics(
                start_date="2025-01-01", end_date="2025-01-07", granularity="WEEK"
            )
            self.assertEqual(len(result), 1)
            self.assertEqual(result[0]["datasets"][0]["data"], [100, 200])
            self.assertEqual(result[0]["datasets"][1]["data"], [0, 0])
            self.assertEqual(result[0]["datasets"][2]["data"], [30, 70])
            self.assertEqual(result[0]["datasets"][3]["data"], [50, 100])
            self.assertEqual(result[0]["datasets"][4]["data"], [0, 0])
            self.assertEqual(result[0]["datasets"][5]["data"], [0, 0])

    def test_get_campaigns(self):
        mock_response = self.generate_magic_mock(
            **{
                "status_code": 200,
                "json_return_value": {
                    "elements": [
                        {"id": "123", "name": "Campaign A"},
                        {"id": "456", "name": "Campaign B"},
                    ]
                },
            }
        )

        patch_request_linkedin = self.generate_patch(
            **{
                "type_object": True,
                "model_patch": self.SocialAccountLinkedin,
                "method_patch": "_request_linkedin",
                "return_value": mock_response,
            }
        )

        with patch_request_linkedin as mock_request_linkedin:
            result = self.SocialAccountLinkedin._get_campaigns(
                start_date=self.start_datetime,
                end_date=self.end_datetime,
                campaign_ids=["123"],
            )
            self.assertEqual(len(result), 2)
            self.assertEqual(result[0]["id"], "123")
            self.assertEqual(result[1]["id"], "456")
            mock_request_linkedin.assert_called_once()

        patch_request_linkedin_failed = self.generate_patch(
            **{
                "type_object": True,
                "model_patch": self.SocialAccountLinkedin,
                "method_patch": "_request_linkedin",
                "return_value": self.generate_magic_mock(
                    **{
                        "status_code": 403,
                    }
                ),
            }
        )
        with patch_request_linkedin_failed as mock_request_linkedin_failed:
            with self.assertRaises(ValidationError):
                self.SocialAccountLinkedin._get_campaigns(
                    start_date=self.start_datetime,
                    end_date=self.end_datetime,
                    campaign_ids=["420"],
                )
            mock_request_linkedin_failed.assert_called_once()

    def test_get_statistics(self):
        mock_response = self.generate_magic_mock(
            **{
                "status_code": 200,
                "json_return_value": {
                    "elements": [
                        {
                            "campaign": "123",
                            "statistics": {"clickCount": 100, "impressionCount": 500},
                        },
                        {
                            "campaign": "456",
                            "statistics": {"clickCount": 200, "impressionCount": 600},
                        },
                    ]
                },
            }
        )
        patch_request_linkedin = self.generate_patch(
            **{
                "type_object": True,
                "model_patch": self.SocialAccountLinkedin,
                "method_patch": "_request_linkedin",
                "return_value": mock_response,
            }
        )
        with patch_request_linkedin as mock_request_linkedin:
            result = self.SocialAccountLinkedin._get_statistics(
                ads_ids=["123", "456"],
                start_date=self.start_datetime,
                end_date=self.end_datetime,
            )
            self.assertEqual(len(result), 2)
            self.assertEqual(result[0]["campaign"], "123")
            self.assertEqual(result[1]["campaign"], "456")
            mock_request_linkedin.assert_called_once()

        patch_request_linkedin_failed = self.generate_patch(
            **{
                "type_object": True,
                "model_patch": self.SocialAccountLinkedin,
                "method_patch": "_request_linkedin",
                "return_value": self.generate_magic_mock(
                    **{
                        "status_code": 403,
                    }
                ),
            }
        )
        with patch_request_linkedin_failed as mock_request_linkedin_failed:
            with self.assertRaises(ValidationError):
                self.SocialAccountLinkedin._get_statistics(
                    ads_ids=["423", "756"],
                    start_date=self.start_datetime,
                    end_date=self.end_datetime,
                )
            mock_request_linkedin_failed.assert_called_once()

    def test_get_statistics_ads(self):
        ads_ids = [123, 456]
        expected_result = [{"mock": "data"}]
        patch_get_statistics = self.generate_patch(
            **{
                "type_object": True,
                "model_patch": self.SocialAccount,
                "method_patch": "_get_statistics",
                "return_value": expected_result,
            }
        )

        with patch_get_statistics as mock_get_statistics:
            result = self.SocialAccountLinkedin._get_statistics_ads(
                ads_ids, self.start_datetime, self.end_datetime
            )
            self.assertEqual(result, expected_result)
            mock_get_statistics.assert_called_once()

    def test_load_ads(self):
        patch_request_linkedin = self.generate_patch(
            **{
                "type_object": True,
                "model_patch": self.SocialAccountLinkedin,
                "method_patch": "_request_linkedin",
                "return_value": self.generate_magic_mock(
                    **{
                        "status_code": 200,
                        "json_return_value": {
                            "elements": [
                                {
                                    "id": 1,
                                    "reference": "ref1",
                                    "campaign": "urn:li:sponsoredCampaign:123",
                                    "changeAuditStamps": {
                                        "created": {"time": 1735689600000}
                                    },
                                    "servingStatuses": ["ACTIVE"],
                                }
                            ]
                        },
                    }
                ),
            }
        )
        patch_get_posts = self.generate_patch(
            **{
                "model_patch": PATCH_ACCOUNT_LINKEDIN.format("_get_posts"),
                "return_value": {
                    "ref1": {
                        "id": "ref1",
                        "specificContent": {
                            "com.linkedin.ugc.ShareContent": {
                                "shareCommentary": {"text": "Test post"}
                            }
                        },
                    }
                },
            }
        )
        patch_get_campaigns = self.generate_patch(
            **{
                "model_patch": PATCH_ACCOUNT_LINKEDIN.format("_get_campaigns"),
                "return_value": [
                    {
                        "id": 123,
                        "account": "urn:li:sponsoredAccount:999",
                    }
                ],
            }
        )
        patch_get_statistics_ads = self.generate_patch(
            **{
                "model_patch": PATCH_ACCOUNT_LINKEDIN.format("_get_statistics_ads"),
                "return_value": [
                    {
                        "pivotValues": ["urn:li:sponsoredAccount:1"],
                        "clicks": 10,
                    }
                ],
            }
        )
        patch_get_default_filter_date = self.generate_patch(
            **{
                "model_patch": PATCH_ACCOUNT.format("_get_default_filter_date"),
                "method_patch": "_get_default_filter_date",
                "side_effect": (
                    lambda s, e, time_date=False: (
                        self.start_datetime,
                        self.end_datetime,
                    )
                    if not time_date
                    else (self.start_datetime, self.end_datetime)
                ),
            }
        )
        with (
            patch_request_linkedin as mock_request_linkedin,
            patch_get_posts as mock_get_posts,
            patch_get_campaigns as mock_get_campaigns,
            patch_get_statistics_ads as mock_get_statistics_ads,
            patch_get_default_filter_date as mock_get_default_filter_date,
        ):
            result = self.SocialAccountLinkedin._load_ads(
                start_date=self.start_datetime, end_date=self.end_datetime
            )
            self.assertEqual(len(result), 1)
            self.assertEqual(result[0]["id"], 1)
            self.assertEqual(result[0]["post"]["name"], "Test post")
            self.assertEqual(result[0]["campaign"]["id"], 123)
            self.assertEqual(result[0]["statistic"]["clicks"], 10)
            self.assertIn("url", result[0])
            mock_request_linkedin.assert_called_once()
            mock_get_statistics_ads.assert_called_once()
            mock_get_campaigns.assert_called_once()
            mock_get_posts.assert_called_once()
            mock_get_default_filter_date.assert_called_once()

        patch_request_linkedin_failed = self.generate_patch(
            **{
                "type_object": True,
                "model_patch": self.SocialAccountLinkedin,
                "method_patch": "_request_linkedin",
                "return_value": self.generate_magic_mock(**{"status_code": 403}),
            }
        )
        with patch_request_linkedin_failed as mock_request_linkedin_failed:
            with self.assertRaises(ValidationError):
                self.SocialAccountLinkedin._load_ads(
                    start_date=self.start_datetime, end_date=self.end_datetime
                )
            mock_request_linkedin_failed.assert_called_once()

    def test_get_restli_client(self):
        result = self.SocialAccountLinkedin._get_restli_client()
        self.assertIsInstance(result, RestliClient)

    @patch(PATCH_ACCOUNT_LINKEDIN.format("_request_linkedin"))
    def test_validate_linkedin_access_token(self, mock_request_linkedin):
        mock_request_linkedin.return_value = {"active": True}
        result = self.SocialAccountLinkedin.validate_linkedin_access_token("token")
        self.assertTrue(result)

        mock_request_linkedin.return_value = {"active": False}
        result = self.SocialAccountLinkedin.validate_linkedin_access_token("token")
        self.assertFalse(result)

        self.assertEqual(mock_request_linkedin.call_count, 2)

    @patch(PATCH_ACCOUNT_LINKEDIN.format("_get_restli_client"))
    @patch(PATCH_ACCOUNT_LINKEDIN.format("_prepare_images_for_post"))
    @patch(PATCH_ACCOUNT_LINKEDIN.format("_prepare_videos_for_post"))
    def test_create_restclient_linkedin(
        self, mock_videos, mock_images, mock_get_restli_client
    ):
        mock_client = Mock()
        mock_images.image_datas = ["dataimage,1", "dataimage,2", "dataimage,3"]
        mock_videos.return_value = []
        mock_response = Mock(status_code=201, entity_id="XYZ123")
        mock_client.create.return_value = mock_response
        mock_get_restli_client.return_value = mock_client
        result = self.SocialAccountLinkedin.create_restclient_linkedin(
            resource_path="/",
            message="",
            image_ids=[],
            video_ids=[],
        )
        self.assertEqual(result, "XYZ123")

        mock_images.return_value = []
        mock_videos.return_value = [4, 5, 6]
        mock_response = Mock(status_code=201, entity_id="XYZ123")
        mock_client.create.return_value = mock_response
        mock_get_restli_client.return_value = mock_client
        result = self.SocialAccountLinkedin.create_restclient_linkedin(
            resource_path="/",
            message="",
            image_ids=[],
            video_ids=[],
        )
        self.assertEqual(result, "XYZ123")

        mock_response = Mock(status_code=201, entity_id=None)
        mock_client.create.return_value = mock_response
        mock_get_restli_client.return_value = mock_client
        result = self.SocialAccountLinkedin.create_restclient_linkedin(
            resource_path="/",
            message="",
            image_ids=[],
            video_ids=[],
        )
        self.assertFalse(result)

        self.assertEqual(mock_images.call_count, 3)
        self.assertEqual(mock_videos.call_count, 3)

    def test_get_default_filter_date(self):
        result = self.SocialAccountLinkedinData._get_default_filter_date(
            start_date=datetime.now(),
            end_date=datetime.now() + timedelta(days=30),
            time_date=True,
        )
        self.assertIsInstance(result, tuple)

    @patch("odoo.addons.social_media_linkedin.models.social_account.requests.request")
    def test_request_linkedin(self, mock_request):
        url_test = "https://api-fake.linkedin.com/v2/test"
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.url = url_test
        mock_request.return_value = mock_response

        result = self.SocialAccount._request_linkedin(
            complete_url=url_test,
            return_json=True,
            params_fields=["authors"],
            params_values={
                "q": "authors",
                "authors": ["urn:li:organization:123456789"],
            },
        )
        self.assertEqual(result, mock_response.json())

        mock_request._URL_V2_LINKEDIN = "https://api-fake.linkedin.com"
        result = self.SocialAccount._request_linkedin(
            linkedin_v2=True,
            return_json=True,
            endpoint="/test",
            params_fields=["authors"],
            params_values={
                "q": "authors",
                "authors": ["urn:li:organization:123456789"],
            },
        )
        self.assertEqual(result, mock_response.json())

        mock_request._URL_REST_LINKEDIN = "https://api-rest-fake.linkedin.com"
        result = self.SocialAccount._request_linkedin(
            token="fake-token",
            return_json=True,
            endpoint="/test-api-rest",
            params_fields=["authors"],
            params_values={
                "q": "authors",
                "authors": ["urn:li:organization:123456789"],
            },
        )
        self.assertEqual(result, mock_response.json())

        self.assertEqual(mock_request.call_count, 3)

    @patch(PATCH_ACCOUNT_LINKEDIN.format("_load_ads"))
    @patch(PATCH_ACCOUNT_LINKEDIN.format("search"))
    def test_load_ads_accounts(self, mock_search, mock_load_ads):
        mock_load_ads_data = MagicMock()
        mock_load_ads_data.ads_linkedin = [
            {
                "media_type": "linkedin",
                "statistic": {"clicks": 10},
            }
        ]
        mock_load_ads.return_value = mock_load_ads_data
        mock_search.return_value = [self.SocialAccountLinkedin]
        self.SocialAccount._load_ads_accounts()
        self.assertEqual(mock_search.call_count, 1)

    def test_unique_account(self):
        with self.assertRaises(ValidationError):
            self.SocialAccountLinkedin.unique_account(
                linkedin_client_id="fake-client-id", linkedin_secret="fake-secret"
            )

    def test_update_account(self):
        res = self.SocialAccountLinkedin.update_account()
        self.assertEqual(res["context"]["default_linkedin_client"], "fake-client-id")
        self.assertEqual(res["context"]["default_linkedin_secret"], "fake-secret")

    def test_refresh_token(self):
        fake_response = {
            "access_token": "fake-access-token",
            "refresh_token": "fake-refresh-token",
            "expires_in": 3600,
        }
        with self._mock_linkedin(
            return_value=fake_response, account=self.SocialAccountLinkedin
        ) as mock_request:
            self.SocialAccountLinkedin._refresh_token()
            mock_value = mock_request.return_value
            self.assertEqual(mock_value.get("access_token"), "fake-access-token")
            self.assertEqual(mock_value.get("refresh_token"), "fake-refresh-token")
            self.assertEqual(mock_value.get("expires_in"), 3600)
            mock_request.assert_called_once()

        mock_response = MagicMock()
        mock_response.text.return_value = "Error"
        with self._mock_linkedin(
            return_value=mock_response, account=self.SocialAccountLinkedin
        ) as mock_request:
            with self.assertRaises(ValidationError):
                self.SocialAccountLinkedin._refresh_token()

            mock_request.assert_called_once()

    @patch(PATCH_ACCOUNT_LINKEDIN.format("_request_linkedin"))
    def test_get_access_token_linkedin(self, mock_request_linkedin):
        mock_request_linkedin.return_value = "fake-csrf-token"
        result = self.SocialAccountLinkedin.get_access_token_linkedin(
            "CODE", "/web", {"state": "fake-csrf-token"}
        )
        self.assertEqual(result[2], "fake-csrf-token")

    def test_get_account_linkedin(self):
        organization_request_linkedin = {
            "elements": [{"organization": "organization:123456789"}]
        }
        organization_logo_mock = MagicMock()
        organization_logo_mock.status_code = 200
        organization_logo_mock.content = b"fake image data"
        organization_name = "Organization Test"
        organization_id = "organization123456789"
        response_organization = {
            "id": organization_id,
            "vanityName": organization_name,
            "name": {"localized": {"es_ES": organization_name}},
            "logoV2": {
                "original~": {
                    "elements": [
                        {
                            "artifact": "logo_400_400/image_organization123456789",
                            "identifiers": [
                                {
                                    "identifier": "https://www.medias.com/logo_400_400/image_organization123456789"
                                }
                            ],
                        }
                    ]
                }
            },
        }
        patch_request_linkedin = self.get_patch_exceptions_linkedin(
            side_effect=[
                organization_request_linkedin,
                response_organization,
                organization_logo_mock,
            ]
        )
        with patch_request_linkedin as mock_request:
            res = self.SocialAccount.get_account_linkedin("fake-access-token")
            self.assertEqual(res[0]["id"], organization_id)
            self.assertEqual(res[0]["localizedName"], organization_name)
            self.assertEqual(res[0]["vanityName"], organization_name)
            self.assertTrue(res[0]["logo"])
            self.assertEqual(mock_request.call_count, 3)

    def test_get_url_redirect(self):
        with patch(
            "odoo.models.BaseModel.get_base_url",
            autospec=True,
            return_value=self.url_callback,
        ) as base_url:
            result = self.wizard_account_id._get_url_redirect()
            self.assertEqual(result, self.url_callback)
            base_url.assert_called_once()

        with patch(
            PATCH_WIZARD_ACCOUNT.format("_get_url_redirect"), autospec=True
        ) as redirect_super:
            self.WizardAccount._get_url_redirect()
            redirect_super.assert_called_once()

    def test_generate_code(self):
        result = self.wizard_account_id._generate_code()
        self.assertEqual(len(result), 10)

    def test_action_add_account(self):
        with patch.object(
            type(self.wizard_account_id),
            "_get_url_redirect",
            return_value=self.url_callback,
        ), patch.object(
            type(self.wizard_account_id),
            "_generate_code",
            return_value="fake-code-token",
        ):
            result = self.wizard_account_id._action_add_account()
            self.assertIn("fake-client-id", result["url"])
            self.assertEqual(result["type"], "ir.actions.act_url")

            result = self.wizard_account_id.with_context(
                only_url=True
            )._action_add_account()
            self.assertIn("fake-client-id", result)

    def test_action_valid_add_account(self):
        with patch.object(type(self.SocialAccount), "unique_account") as uni_acc:
            self.wizard_account_id._action_valid_add_account()
            uni_acc.assert_called_once()

    def test_update_account_keys(self):
        with patch.object(
            type(self.wizard_account_id),
            "_update_account",
        ) as upd_acc:
            self.wizard_account_id._update_account()
            upd_acc.assert_called_once()

        self.wizard_account_id.write(
            {
                "update_keys": True,
                "account_id": self.SocialAccountLinkedin.id,
            }
        )
        result = self.wizard_account_id._update_account()
        self.assertEqual(result["type"], "ir.actions.act_url")
        self.assertEqual(result["target"], "self")
        self.assertEqual(
            self.SocialAccountLinkedin.linkedin_client_id,
            self.wizard_account_id.linkedin_client,
        )
        self.assertEqual(
            self.SocialAccountLinkedin.linkedin_secret,
            self.wizard_account_id.linkedin_secret,
        )

    @patch(PATCH_SOCIAL_BASE_MIXIN.format("_notify_user_client"))
    @patch(PATCH_ACCOUNT_LINKEDIN.format("_refresh_token"))
    def test_update_account_token(self, mock_refresh_linkedin, mock_notify_user):
        self.wizard_account_id.write(
            {
                "update_keys": False,
                "update_token": True,
                "account_id": self.SocialAccountLinkedin.id,
            }
        )
        mock_refresh_linkedin.return_value = {
            "access_token": "fake-access-token",
            "refresh_token": "fake-refresh-token",
            "expires_in": 1597560000,
        }
        self.wizard_account_id._update_account()
        mock_notify_user.assert_called_once()
        self.assertEqual(self.SocialAccountLinkedin.access_token, "fake-access-token")
        self.assertEqual(
            self.SocialAccountLinkedin.refresh_access_token, "fake-refresh-token"
        )

    @patch(PATCH_ACCOUNT_LINKEDIN.format("get_account_linkedin"))
    def test_update_account_organization(self, mock_linkedin):
        self.wizard_account_id.write(
            {
                "account_id": self.SocialAccountLinkedin.id,
            }
        )
        mock_linkedin.return_value = [
            {
                "localizedName": "Localized X",
                "vanityName": "Vanity X",
                "logo": self.VALID_PNG_B64,
            }
        ]
        self.wizard_account_id._update_account()
        self.assertEqual(self.SocialAccountLinkedin.name, "Localized X")
        self.assertEqual(self.SocialAccountLinkedin.username, "Vanity X")
        mock_linkedin.assert_called_once()

    def test_get_csrf_state_token(self):
        fake_code_hmac = "fake-hmac-code"
        with patch.object(
            type(self.wizard_account_id), "_generate_code", autospec=True
        ) as mock_fake_code, patch(
            PATCH_WIZARD_ACCOUNT_LINKEDIN.format("hmac"),
            autospec=True,
            return_value=fake_code_hmac,
        ) as mock_hmac:
            result = self.wizard_account_id._get_csrf_state_token()
            self.assertEqual(result, fake_code_hmac)
            mock_hmac.assert_called_once()
            mock_fake_code.assert_called_once()

        with patch(
            PATCH_WIZARD_ACCOUNT.format("_get_csrf_state_token"), autospec=True
        ) as mock_hmac_super:
            self.WizardAccount._get_csrf_state_token()
            mock_hmac_super.assert_called_once()

    def test_compute_csrf_state_token(self):
        expected_token = "fake-csrf-token"
        with patch.object(
            type(self.wizard_account_id),
            "_get_csrf_state_token",
            autospec=True,
            return_value=expected_token,
        ) as mocked_get_token:
            self.wizard_account_id._compute_csrf_state_token()
            value = self.wizard_account_id.csrf_state_token
            mocked_get_token.assert_called_once_with(self.wizard_account_id)
            self.assertEqual(value, expected_token)

    def test_action_associate_social_account(self):
        action_fake_url = {
            "type": "ir.actions.act_url",
            "url": "https://test.example/redirect",
            "target": "self",
        }
        with patch.object(
            type(self.wizard_account_id),
            "_action_valid_add_account",
            autospec=True,
        ) as mocked_valid, patch.object(
            type(self.wizard_account_id),
            "_action_add_account",
            autospec=True,
            return_value=action_fake_url,
        ) as mocked_add:
            result = self.wizard_account_id.action_associate_social_account()
            mocked_valid.assert_called_once_with(self.wizard_account_id)
            mocked_add.assert_called_once_with(self.wizard_account_id)
            self.assertEqual(result, action_fake_url)

    def test_create_account_linkedin_failed(self):
        with self.assertRaises(ValidationError) as ctx:
            self.SocialAccount.create_account_linkedin(
                "fake-client-id",
                "fake-secret",
                MagicMock(text="Error token"),
            )
        self.assertIn("Creating account", str(ctx.exception))

    def test_create_account_linkedin(self):
        fake_organization = self.generate_magic_mock(
            **{
                "return_value": {
                    "vanityName": "Vanity X",
                }
            }
        )

        def search_side_effect(recordset, domain=None, *args, **kwargs):
            if recordset._name == "wizard.social.account":
                return self.wizard_account_id
            return self.SocialAccount

        with (
            patch(
                "odoo.models.BaseModel.search",
                autospec=True,
                side_effect=search_side_effect,
            ) as mock_search,
            patch(
                "odoo.models.BaseModel.create",
                autospec=True,
                return_value=self.SocialAccountLinkedin,
            ) as mock_create,
            patch("odoo.models.BaseModel.unlink", autospec=True) as mock_unlink,
            patch.object(
                type(self.SocialAccountLinkedin),
                "get_account_linkedin",
                autospec=True,
                return_value=[fake_organization],
            ) as mock_account_linkedin,
        ):
            self.SocialAccount.create_account_linkedin(
                "fake-client-id",
                "fake-secret",
                {"access_token": "fake-access-token"},
            )
            self.assertEqual(mock_search.call_count, 2)
            mock_account_linkedin.assert_called_once()
            mock_create.assert_called_once()
            mock_unlink.assert_called_once()

    def test_validate_access_token(self):
        patch_notify_user = patch(PATCH_SOCIAL_BASE_MIXIN.format("_notify_user_client"))
        self.SocialAccountLinkedin.expire_access_token_date = (
            datetime.now() + timedelta(days=-10)
        ).date()
        with patch(
            PATCH_ACCOUNT.format("validate_access_token")
        ) as mock_super, patch.object(
            type(self.SocialAccount),
            "validate_linkedin_access_token",
            autospec=True,
            return_value=True,
        ) as mock_validate_token, patch_notify_user as mock_notify_user:
            self.SocialAccountLinkedin.validate_access_token()
            mock_super.assert_called_once()
            mock_validate_token.assert_called_once()
            mock_notify_user.assert_called_once()

        self.SocialAccountLinkedin.expire_access_token_date = (
            datetime.now() + timedelta(days=1)
        ).date()
        self.SocialAccountLinkedin.refresh_token_expires_in = (
            datetime.now() + timedelta(days=1)
        ).date()
        with patch(
            PATCH_ACCOUNT.format("validate_access_token")
        ) as mock_super_failed, patch_notify_user as mock_notify_user_failed:
            self.SocialAccountLinkedin.validate_access_token()
            mock_super_failed.assert_called_once()
            mock_notify_user_failed.assert_called_once()