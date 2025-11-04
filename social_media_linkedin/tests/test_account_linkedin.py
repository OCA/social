# Copyright 2025 Binhex <https://www.binhex.cloud>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).


from datetime import datetime, timedelta
from unittest.mock import MagicMock, Mock, patch

from linkedin_api.clients.restli.client import RestliClient

from odoo.exceptions import ValidationError

from odoo.addons.social_media_base.social_utils import (
    _generate_timestamps,
)
from odoo.addons.social_media_base.tests.test_social_common import (
    PATCH_SOCIAL_BASE_MIXIN,
)
from odoo.addons.social_media_linkedin.models.social_account import (
    SocialAccount,
)
from odoo.addons.social_media_linkedin.tests.test_common_linkedin import (
    PATCH_ACCOUNT_LINKEDIN,
    TestSocialCommonLinkedin,
)

from ..social_linkedin_utils import (
    _FIELDS_CAMPAIGN_LINKEDIN,
    _FIELDS_STATISTIC_LINKEDIN,
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

        with self._mock_linkedin(
            return_value=fake_response, account=self.SocialAccountLinkedin
        ) as mock_request:
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

        with self._mock_linkedin(
            return_value=fake_response, account=self.SocialAccountLinkedin
        ) as mock_request:
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
        mock_response = Mock()
        mock_response.status_code = 201
        method_asset = "_prepare_url_upload_asset"

        def mock_upload_image_video(mock_upload_asset):
            return self._mock_linkedin(
                return_value=mock_upload_asset,
                attribute=method_asset,
                account=self.SocialAccountLinkedin,
            ), self._mock_linkedin(
                return_value=mock_response, account=self.SocialAccountLinkedin
            )

        val1, val2 = mock_upload_image_video(mock_upload_asset_image)

        with val1, val2:
            images = self.SocialAccountLinkedin._prepare_images_for_post(
                image_ids=[self.image_base64]
            )
            self.assertEqual(len(images), 1)
            self.assertEqual(images[0], self.mediaAsset.format("XYZ"))

        val1, val2 = mock_upload_image_video(mock_upload_asset_video)

        with val1, val2:
            videos = self.SocialAccountLinkedin._prepare_videos_for_post(
                video_ids=[self.video_mock]
            )
            self.assertEqual(len(videos), 1)
            self.assertEqual(videos[0], self.mediaAsset.format("VID123"))

    @patch(PATCH_ACCOUNT_LINKEDIN.format("_request_linkedin"))
    def test_get_posts(self, mock_request_linkedin):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
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
        }

        mock_request_linkedin.return_value = mock_response

        linkedin_account = self.SocialAccountLinkedin
        posts = linkedin_account._get_posts()

        self.assertEqual(len(posts), 2)
        self.assertEqual(posts[0]["id"], "123")
        self.assertEqual(posts[1]["id"], "456")
        self.assertEqual(posts[0]["share_content"]["text"], "Post 1")
        self.assertEqual(posts[1]["share_content"]["text"], "Post 2")

        mock_request_linkedin.assert_called_once_with(
            endpoint="/ugcPosts",
            headers=self.media_linkedin_id._get_linkedin_headers(
                linkedin_account.access_token
            ),
            params_fields=["q", "authors"],
            params_values={
                "q": "authors",
                "authors": [
                    f"urn:li:organization:{linkedin_account.linkedin_account_id}"
                ],
            },
            linkedin_v2=True,
            return_json=False,
        )

        mock_response.status_code = 400
        with self.assertRaises(ValidationError):
            linkedin_account._get_posts()

    @patch(PATCH_ACCOUNT_LINKEDIN.format("_get_entity_share_statistics"))
    @patch(PATCH_ACCOUNT_LINKEDIN.format("_get_default_filter_date"))
    def test_get_chart_account_statistics(
        self, mock_get_default_filter_date, mock_get_entity_share_statistics
    ):
        mock_get_default_filter_date.return_value = (
            "2025-01-01T00:00:00",
            "2025-01-07T23:59:59",
        )

        mock_get_entity_share_statistics.return_value = [
            {
                "totalShareStatistics": {
                    "clickCount": 100,
                    "shareCount": 50,
                    "likeCount": 30,
                }
            },
            {
                "totalShareStatistics": {
                    "clickCount": 200,
                    "shareCount": 100,
                    "likeCount": 70,
                }
            },
        ]

        linkedin_account = self.SocialAccountLinkedin

        result = linkedin_account._get_chart_account_statistics(
            start_date="2025-01-01", end_date="2025-01-07", granularity="WEEK"
        )

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["datasets"][0]["data"], [100, 200])
        self.assertEqual(result[0]["datasets"][1]["data"], [50, 100])
        self.assertEqual(result[0]["datasets"][2]["data"], [30, 70])

    @patch(PATCH_ACCOUNT_LINKEDIN.format("_request_linkedin"))
    def test_get_campaigns(self, mock_request_linkedin):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "elements": [
                {"id": "123", "name": "Campaign A"},
                {"id": "456", "name": "Campaign B"},
            ]
        }
        mock_request_linkedin.return_value = mock_response
        linkedin_account = self.SocialAccountLinkedin

        startDate = datetime(2025, 1, 1)
        endDate = datetime(2025, 1, 31)

        result = linkedin_account._get_campaigns(
            start_date=startDate, end_date=endDate, campaign_ids=["123"]
        )

        start_time, end_time = _generate_timestamps(startDate, endDate)

        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["id"], "123")
        self.assertEqual(result[1]["id"], "456")
        start_date = f"(startDate:(values:{start_time})"
        end_date = f"endDate:(values:{end_time})"
        mock_request_linkedin.assert_called_once_with(
            endpoint="/adCampaignsV2",
            headers=self.media_linkedin_id._get_linkedin_headers(
                linkedin_account.access_token
            ),
            params_fields=["q", "search", "fields", "count"],
            params_values={
                "q": "search",
                "search": f"{start_date},{end_date},"
                "test:true,campaigns:(values:List(123)))",
                "fields": _FIELDS_CAMPAIGN_LINKEDIN,
                "count": 100,
            },
            params_values_char_ignore={"search": [{"1,2,3,4,5,6,7": ":"}]},
            return_json=False,
            linkedin_v2=True,
            format_quote=True,
        )

        with self.assertRaises(ValidationError):
            mock_request_linkedin.return_value = MagicMock(status_code=403)
            linkedin_account._get_campaigns(
                start_date=startDate, end_date=endDate, campaign_ids=["420"]
            )

    @patch(PATCH_ACCOUNT_LINKEDIN.format("_request_linkedin"))
    def test_get_statistics(self, mock_request_linkedin):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
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
        }
        mock_request_linkedin.return_value = mock_response

        linkedin_account = self.SocialAccountLinkedin

        result = linkedin_account._get_statistics(
            ads_ids=["123", "456"],
            start_date=datetime(2025, 1, 1),
            end_date=datetime(2025, 1, 31),
        )

        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["campaign"], "123")
        self.assertEqual(result[1]["campaign"], "456")
        start_range = "(start:(year:2025,month:1,day:1)"
        end_range = "end:(year:2025,month:1,day:31))"
        mock_request_linkedin.assert_called_once_with(
            endpoint="/adAnalyticsV2",
            headers=linkedin_account.media_id._get_linkedin_headers(
                linkedin_account.access_token
            ),
            params_fields=[
                "q",
                "pivots",
                "timeGranularity",
                "dateRange",
                "fields",
                "count",
                "accounts",
            ],
            params_values={
                "q": "statistics",
                "pivots": ["CREATIVE"],
                "timeGranularity": "ALL",
                "dateRange": f"{start_range},{end_range}",
                "fields": _FIELDS_STATISTIC_LINKEDIN,
                "count": 100,
                "accounts": [
                    "urn:li:sponsoredAccount:123",
                    "urn:li:sponsoredAccount:456",
                ],
            },
            params_values_char_ignore={"dateRange": [{"all": ":"}]},
            return_json=False,
            linkedin_v2=True,
            format_quote=True,
        )

        with self.assertRaises(ValidationError):
            mock_request_linkedin.return_value = MagicMock(status_code=403)
            linkedin_account._get_statistics(
                ads_ids=["423", "756"],
                start_date=datetime(2025, 1, 1),
                end_date=datetime(2025, 1, 31),
            )

    @patch.object(SocialAccount, "_get_statistics")
    def test_get_statistics_ads_calls_internal_method(self, mock_get_statistics):
        ads_ids = [123, 456]
        start_date = datetime(2024, 1, 1)
        end_date = datetime(2024, 1, 31)

        expected_result = [{"mock": "data"}]
        mock_get_statistics.return_value = expected_result

        result = self.SocialAccountLinkedin._get_statistics_ads(
            ads_ids, start_date, end_date
        )

        mock_get_statistics.assert_called_once_with(
            ads_ids=ads_ids,
            start_date=start_date,
            end_date=end_date,
        )
        self.assertEqual(result, expected_result)

    @patch(PATCH_ACCOUNT_LINKEDIN.format("_get_statistics_ads"))
    @patch(PATCH_ACCOUNT_LINKEDIN.format("_get_campaigns"))
    @patch(PATCH_ACCOUNT_LINKEDIN.format("_get_posts"))
    @patch(PATCH_ACCOUNT_LINKEDIN.format("_request_linkedin"))
    def test_load_ads(
        self,
        mock_request_linkedin,
        mock_get_posts,
        mock_get_campaigns,
        mock_get_statistics_ads,
    ):
        # Arrange
        fake_ads = [
            {
                "id": 1,
                "reference": "ref1",
                "campaign": "urn:li:sponsoredCampaign:123",
                "changeAuditStamps": {"created": {"time": 1735689600000}},
                "servingStatuses": ["ACTIVE"],
            }
        ]
        fake_stats = [
            {
                "pivotValues": ["urn:li:sponsoredAccount:1"],
                "clicks": 10,
            }
        ]
        fake_campaigns = [
            {
                "id": 123,
                "account": "urn:li:sponsoredAccount:999",
            }
        ]
        fake_posts = {
            "ref1": {
                "id": "ref1",
                "specificContent": {
                    "com.linkedin.ugc.ShareContent": {
                        "shareCommentary": {"text": "Test post"}
                    }
                },
            }
        }

        mock_request_linkedin.return_value = MagicMock(
            status_code=200, json=lambda: {"elements": fake_ads}
        )
        mock_get_statistics_ads.return_value = fake_stats
        mock_get_campaigns.return_value = fake_campaigns
        mock_get_posts.return_value = fake_posts

        mock_account = MagicMock()
        mock_account.media_type = "linkedin"
        mock_account._get_default_filter_date.side_effect = (
            lambda s, e, time_date=False: ("2025-01-01", "2025-01-31")
            if not time_date
            else (1735689600000, 1738281600000)
        )

        with patch(
            PATCH_ACCOUNT_LINKEDIN.format("_get_default_filter_date"),
            self.SocialAccountLinkedin._get_default_filter_date,
        ):
            mock_account._request_linkedin = mock_request_linkedin
            mock_account._get_statistics_ads = mock_get_statistics_ads
            mock_account._get_campaigns = mock_get_campaigns
            mock_account._get_posts = mock_get_posts

            result = self.SocialAccountLinkedin._load_ads(
                start_date="2025-01-01", end_date="2025-01-31"
            )

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["id"], 1)
        self.assertEqual(result[0]["post"]["name"], "Test post")
        self.assertEqual(result[0]["campaign"]["id"], 123)
        self.assertEqual(result[0]["statistic"]["clicks"], 10)
        self.assertIn("url", result[0])

        with self.assertRaises(ValidationError):
            mock_request_linkedin.return_value = MagicMock(status_code=403)
            self.SocialAccountLinkedin._load_ads(
                start_date="2025-01-01", end_date="2025-01-31"
            )

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

    @patch(PATCH_ACCOUNT_LINKEDIN.format("_request_linkedin"))
    def test_get_account_linkedin(self, mock_request_linkedin):
        mock_request_linkedin.side_effect = [
            {"elements": [{"organization": "urn:li:organization:1153624578"}]},
            {
                "id": "1153624578",
                "vanityName": "userLinkedin",
                "logo": "logo_test",
                "name": {"localized": {"en_US": "ORGANITATION X"}},
            },
            "logo_test",
        ]
        result = self.SocialAccountLinkedin.get_account_linkedin("TOKEN-TEST")
        self.assertEqual(result[0]["id"], "1153624578")
        self.assertEqual(result[0]["localizedName"], "ORGANITATION X")
        self.assertEqual(result[0]["vanityName"], "userLinkedin")
        self.assertIsNone(result[0]["logo"])

    def test_get_url_redirect(self):
        result = self.wizard_account_id._get_url_redirect()
        self.assertEqual(result, self.url_callback)

        with patch.object(type(self.WizardAccount), "_get_url_redirect") as url:
            self.WizardAccount._get_url_redirect()
            url.assert_called_once()

    def test_generate_code(self):
        result = self.wizard_account_id._generate_code()
        self.assertEqual(len(result), 10)

    def test_action_add_account(self):
        with (
            patch.object(
                type(self.wizard_account_id),
                "_get_url_redirect",
                return_value=self.url_callback,
            ),
            patch.object(
                type(self.wizard_account_id),
                "_generate_code",
                return_value="fake-code-token",
            ),
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
