# Copyright 2026 Binhex <https://www.binhex.cloud>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from unittest.mock import MagicMock, patch

from odoo.exceptions import UserError
from odoo.fields import Command

from odoo.addons.social_media_linkedin.tests.test_common_linkedin import (
    PATCH_ACCOUNT_LINKEDIN,
)

from ..hooks import post_init_hook
from ..social_advertising_linkedin_utils import _CHUNK_SIZE_ANALYTICS_LINKEDIN
from .test_common_advertising_linkedin import (
    PATCH_ADVERTISING_ACCOUNT_LINKEDIN,
    TestSocialCommonAdvertisingLinkedin,
)


class TestSocialAccountAdvertisingLinkedin(TestSocialCommonAdvertisingLinkedin):
    def test_get_advertising_account_is_the_one_in_use(self):
        account = self.SocialAccountLinkedin
        self.assertEqual(
            account._get_linkedin_advertising_account(),
            "urn:li:sponsoredAccount:999",
        )

    def test_get_advertising_account_without_one_in_use(self):
        """Nothing is guessed: without a chosen one there is no scope."""
        account = self.SocialAccountLinkedin
        self.AdvertisingAccountLinkedin.write({"is_current": False})
        self.assertFalse(account._get_linkedin_advertising_account())
        with self.assertRaises(UserError) as error:
            account._require_linkedin_ad_account_id()
        self.assertIn("No LinkedIn advertising account is in use", str(error.exception))

    def test_environment_change_drops_the_account_in_use(self):
        """A production account never keeps the test advertising account."""
        account = self.SocialAccountLinkedin
        account.write({"environment": "production"})
        self.assertFalse(self.AdvertisingAccountLinkedin.is_current)
        self.assertFalse(account.advertising_account_urn)
        self.assertFalse(account._get_linkedin_advertising_account())

    def test_import_campaigns_without_an_advertising_account_in_use(self):
        account = self.SocialAccountLinkedin
        self.AdvertisingAccountLinkedin.write({"is_current": False})
        res = account.action_import_campaigns()
        self.assertFalse(res["success"])
        self.assertIn("No LinkedIn advertising account is in use", res["message"])
        self.assertEqual(res["campaigns"], 0)

    def test_import_campaigns_without_the_ads_scope(self):
        """A missing scope is explained instead of ending in a bare 403."""
        account = self.SocialAccountLinkedin
        account.linkedin_granted_scopes = "w_member_social"
        res = account.action_import_campaigns()
        self.assertFalse(res["success"])
        self.assertIn("r_ads", res["message"])

    def test_fetch_advertising_accounts_without_the_ads_scope(self):
        account = self.SocialAccountLinkedin
        account.linkedin_granted_scopes = "w_member_social"
        with self.assertRaises(UserError) as error:
            account._fetch_advertising_accounts()
        self.assertIn("r_ads", str(error.exception))

    def test_fetch_advertising_accounts_maps_the_payload(self):
        account = self.SocialAccountLinkedin
        users_response = self.generate_magic_mock(
            **{
                "status_code": 200,
                "json_return_value": {
                    "paging": {"total": 1},
                    "elements": [{"account": "urn:li:sponsoredAccount:2"}],
                },
            }
        )
        production_account = self.generate_magic_mock(
            **{
                "status_code": 200,
                "json_return_value": {
                    "id": 2,
                    "test": False,
                    "name": "Dunder Mifflin",
                    "currency": "USD",
                    "status": "ACTIVE",
                    "type": "BUSINESS",
                    "reference": "urn:li:organization:2414183",
                    "servingStatuses": ["BILLING_HOLD"],
                },
            }
        )
        patch_request_linkedin = self.generate_patch(
            **{
                "type_object": True,
                "model_patch": account,
                "method_patch": "_request_linkedin",
                "side_effect": [users_response, production_account],
            }
        )
        with patch_request_linkedin:
            account._sync_advertising_accounts()
        advertising_account = account.advertising_account_ids.filtered(
            lambda record: record.remote_ref == "urn:li:sponsoredAccount:2"
        )
        self.assertEqual(advertising_account.name, "Dunder Mifflin")
        self.assertEqual(advertising_account.environment, "production")
        self.assertEqual(advertising_account.currency_id, self.env.ref("base.USD"))
        self.assertEqual(advertising_account.linkedin_status, "ACTIVE")
        self.assertEqual(advertising_account.linkedin_type, "BUSINESS")
        self.assertEqual(advertising_account.linkedin_serving_status, "BILLING_HOLD")
        self.assertEqual(
            advertising_account.linkedin_reference, "urn:li:organization:2414183"
        )
        self.assertFalse(
            advertising_account.is_current,
            msg="Fetching must not choose an advertising account by itself.",
        )

    def test_fetch_ad_entities_follows_the_cursor(self):
        """The search finders paginate with a token, not with an index."""
        first_page = self.generate_magic_mock(
            **{
                "status_code": 200,
                "json_return_value": {
                    "elements": [{"id": 1}],
                    "metadata": {"nextPageToken": "token-2"},
                },
            }
        )
        second_page = self.generate_magic_mock(
            **{
                "status_code": 200,
                "json_return_value": {"elements": [{"id": 2}], "metadata": {}},
            }
        )
        patch_request_linkedin = self.generate_patch(
            **{
                "type_object": True,
                "model_patch": self.SocialAccountLinkedin,
                "method_patch": "_request_linkedin",
                "side_effect": [first_page, second_page],
            }
        )
        with patch_request_linkedin as mock_request_linkedin:
            elements = self.SocialAccountLinkedin._fetch_linkedin_ad_entities(
                "/adAccounts/999/adCampaigns"
            )
        self.assertEqual([element["id"] for element in elements], [1, 2])
        self.assertEqual(mock_request_linkedin.call_count, 2)
        self.assertEqual(
            mock_request_linkedin.call_args.kwargs["params_values"]["pageToken"],
            "token-2",
        )

    def test_get_linkedin_statistics(self):
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
            result = self.SocialAccountLinkedin._get_linkedin_statistics(
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
            with self.assertRaises(UserError):
                self.SocialAccountLinkedin._get_linkedin_statistics(
                    ads_ids=["423", "756"],
                    start_date=self.start_datetime,
                    end_date=self.end_datetime,
                )
            mock_request_linkedin_failed.assert_called_once()

    def test_get_linkedin_statistics_ads(self):
        ads_ids = [123, 456]
        expected_result = [{"mock": "data"}]
        patch_get_linkedin_statistics = self.generate_patch(
            **{
                "type_object": True,
                "model_patch": self.SocialAccount,
                "method_patch": "_get_linkedin_statistics",
                "return_value": expected_result,
            }
        )

        with patch_get_linkedin_statistics as mock_get_linkedin_statistics:
            result = self.SocialAccountLinkedin._get_linkedin_statistics_ads(
                ads_ids, self.start_datetime, self.end_datetime
            )
            self.assertEqual(result, expected_result)
            mock_get_linkedin_statistics.assert_called_once()

    @patch(PATCH_ACCOUNT_LINKEDIN.format("_request_linkedin"))
    @patch(
        PATCH_ADVERTISING_ACCOUNT_LINKEDIN.format("_get_linkedin_advertising_account")
    )
    def test_action_import_campaigns(self, mock_advertising, mock_request_linkedin):
        advertising = "urn:li:sponsoredAccount:999"
        mock_advertising.return_value = advertising
        groups_response = MagicMock(status_code=200)
        groups_response.json.return_value = {
            "elements": [
                {
                    "id": 45,
                    "name": "Imported Group",
                    "account": advertising,
                    "totalBudget": {"amount": "100", "currencyCode": "USD"},
                },
            ],
            "metadata": {},
        }
        campaigns_response = MagicMock(status_code=200)
        campaigns_response.json.return_value = {
            "elements": [
                {
                    "id": 67,
                    "name": "Imported Campaign",
                    "account": advertising,
                    "campaignGroup": "urn:li:sponsoredCampaignGroup:45",
                    "format": "SINGLE_VIDEO",
                    "unitCost": {"amount": "1", "currencyCode": "USD"},
                    "dailyBudget": {"amount": "10", "currencyCode": "USD"},
                },
            ],
            "paging": {"total": 1},
        }
        creatives_response = MagicMock(status_code=200)
        creatives_response.json.return_value = {
            "elements": [
                {
                    "id": "urn:li:sponsoredCreative:888",
                    "content": {"reference": "urn:li:share:5555"},
                    "campaign": "urn:li:sponsoredCampaign:67",
                    "isTest": True,
                },
            ],
            "metadata": {},
        }
        self.SocialPostAccountLinkedin.write({"remote_ref": "urn:li:share:5555"})
        mock_request_linkedin.side_effect = [
            groups_response,
            campaigns_response,
            creatives_response,
        ]
        res = self.SocialAccountLinkedin.action_import_campaigns()
        self.assertTrue(res["success"])
        self.assertEqual(res["groups"], 1)
        self.assertEqual(res["campaigns"], 1)
        self.assertEqual(res["ads"], 1)
        group = self.SocialAdvertisingCampaignGroup.search(
            [("remote_ref", "=", "urn:li:sponsoredCampaignGroup:45")]
        )
        self.assertEqual(group.name, "Imported Group")
        self.assertEqual(group.total_budget, 100)
        self.assertEqual(
            mock_request_linkedin.call_args_list[0].kwargs["endpoint"],
            "/adAccounts/999/adCampaignGroups",
        )
        self.assertEqual(
            mock_request_linkedin.call_args_list[1].kwargs["endpoint"],
            "/adAccounts/999/adCampaigns",
        )
        campaign = self.SocialAdvertisingCampaign.search(
            [("remote_ref", "=", "urn:li:sponsoredCampaign:67")]
        )
        self.assertEqual(campaign.campaign_group_id, group)
        self.assertIn(self.SocialAccountLinkedin, campaign.account_ids)
        self.assertEqual(campaign.daily_budget, 10)
        self.assertEqual(campaign.linkedin_format, "SINGLE_VIDEO")
        self.assertEqual(
            self.SocialPostAccountLinkedin.creative_urn,
            "urn:li:sponsoredCreative:888",
        )
        self.assertEqual(group.campaign_count, 1)
        action = group.action_view_campaigns()
        self.assertEqual(action["domain"], [("campaign_group_id", "=", group.id)])
        mock_request_linkedin.side_effect = [
            groups_response,
            campaigns_response,
            creatives_response,
        ]
        res = self.SocialAccountLinkedin.action_import_campaigns()
        self.assertTrue(res["success"])
        self.assertEqual(res["groups"], 0)
        self.assertEqual(res["campaigns"], 0)
        self.assertEqual(res["ads"], 0)
        self.assertFalse(self.SocialPostAccountLinkedin.social_campaign_id)

    def _import_creatives_response(self, reference, campaign_urn):
        """Return the three responses of an import with a single creative."""
        advertising = "urn:li:sponsoredAccount:999"
        groups_response = MagicMock(status_code=200)
        groups_response.json.return_value = {
            "elements": [
                {
                    "id": 45,
                    "name": "Imported Group",
                    "account": advertising,
                    "totalBudget": {"amount": "100", "currencyCode": "USD"},
                }
            ],
            "paging": {"total": 1},
        }
        campaigns_response = MagicMock(status_code=200)
        campaigns_response.json.return_value = {
            "elements": [
                {
                    "id": 67,
                    "name": "Imported Campaign",
                    "account": advertising,
                    "campaignGroup": "urn:li:sponsoredCampaignGroup:45",
                    "format": "STANDARD_UPDATE",
                    "unitCost": {"amount": "1", "currencyCode": "USD"},
                    "dailyBudget": {"amount": "10", "currencyCode": "USD"},
                }
            ],
            "paging": {"total": 1},
        }
        creatives_response = MagicMock(status_code=200)
        creatives_response.json.return_value = {
            "elements": [
                {
                    "id": "urn:li:sponsoredCreative:888",
                    "content": {"reference": reference},
                    "campaign": campaign_urn,
                    "isTest": True,
                }
            ],
            "metadata": {},
        }
        return [groups_response, campaigns_response, creatives_response]

    @patch(PATCH_ACCOUNT_LINKEDIN.format("_request_linkedin"))
    @patch(
        PATCH_ADVERTISING_ACCOUNT_LINKEDIN.format("_get_linkedin_advertising_account")
    )
    def test_import_campaigns_links_the_campaign_of_an_imported_post(
        self, mock_advertising, mock_request_linkedin
    ):
        """A publication brought from the wall gets its campaign here.

        It has no parent post, so the campaign can only come from the
        creative that promotes it.
        """
        mock_advertising.return_value = "urn:li:sponsoredAccount:999"
        imported = self.SocialPostAccount.create(
            {
                "account_id": self.SocialAccountLinkedin.id,
                "message": "Imported from the wall",
                "remote_ref": "urn:li:share:9999",
                "state": "posted",
            }
        )
        self.assertFalse(imported.post_id)
        responses = self._import_creatives_response(
            "urn:li:share:9999", "urn:li:sponsoredCampaign:67"
        )
        mock_request_linkedin.side_effect = responses
        res = self.SocialAccountLinkedin.action_import_campaigns()
        self.assertEqual(res["ads"], 1)
        self.assertEqual(
            imported.social_campaign_id.remote_ref, "urn:li:sponsoredCampaign:67"
        )
        self.assertEqual(imported.creative_urn, "urn:li:sponsoredCreative:888")
        mock_request_linkedin.side_effect = self._import_creatives_response(
            "urn:li:share:9999", "urn:li:sponsoredCampaign:67"
        )
        res = self.SocialAccountLinkedin.action_import_campaigns()
        self.assertEqual(res["ads"], 0)
        self.assertEqual(
            imported.social_campaign_id.remote_ref, "urn:li:sponsoredCampaign:67"
        )

    @patch(PATCH_ACCOUNT_LINKEDIN.format("_request_linkedin"))
    @patch(
        PATCH_ADVERTISING_ACCOUNT_LINKEDIN.format("_get_linkedin_advertising_account")
    )
    def test_import_campaigns_ignores_an_unknown_campaign(
        self, mock_advertising, mock_request_linkedin
    ):
        mock_advertising.return_value = "urn:li:sponsoredAccount:999"
        imported = self.SocialPostAccount.create(
            {
                "account_id": self.SocialAccountLinkedin.id,
                "message": "Imported from the wall",
                "remote_ref": "urn:li:share:8888",
                "state": "posted",
            }
        )
        mock_request_linkedin.side_effect = self._import_creatives_response(
            "urn:li:share:8888", "urn:li:sponsoredCampaign:404"
        )
        res = self.SocialAccountLinkedin.action_import_campaigns()
        self.assertTrue(res["success"])
        self.assertFalse(imported.social_campaign_id)
        self.assertEqual(imported.creative_urn, "urn:li:sponsoredCreative:888")

    @patch(PATCH_ACCOUNT_LINKEDIN.format("_request_linkedin"))
    @patch(
        PATCH_ADVERTISING_ACCOUNT_LINKEDIN.format("_get_linkedin_advertising_account")
    )
    def test_campaign_pending_changes_hybrid_import(
        self, mock_advertising, mock_request_linkedin
    ):
        advertising = "urn:li:sponsoredAccount:999"
        mock_advertising.return_value = advertising
        currency_usd = self.env.ref("base.USD")
        group = self.SocialAdvertisingCampaignGroup.create(
            {
                "name": "Synced Group",
                "remote_ref": "urn:li:sponsoredCampaignGroup:70",
                "total_budget": 100,
                "currency_id": currency_usd.id,
            }
        )
        campaign = self.SocialAdvertisingCampaign.create(
            {
                "name": "Synced Campaign",
                "campaign_group_id": group.id,
                "media_id": self.media_linkedin_data_id.id,
                "account_ids": [Command.link(self.SocialAccountLinkedin.id)],
                "unit_cost": 1,
                "daily_budget": 10,
                "remote_ref": "urn:li:sponsoredCampaign:71",
            }
        )
        self.assertFalse(campaign.linkedin_needs_update)
        self.assertFalse(group.linkedin_needs_update)
        campaign.write({"unit_cost": 99})
        group.write({"total_budget": 500})
        self.assertTrue(campaign.linkedin_needs_update)
        self.assertTrue(group.linkedin_needs_update)
        groups_response = MagicMock(status_code=200)
        groups_response.json.return_value = {
            "elements": [
                {
                    "id": 70,
                    "name": "Renamed Group In LinkedIn",
                    "account": advertising,
                    "status": "ACTIVE",
                    "totalBudget": {"amount": "300", "currencyCode": "USD"},
                },
            ],
            "paging": {"total": 1},
        }
        campaigns_response = MagicMock(status_code=200)
        campaigns_response.json.return_value = {
            "elements": [
                {
                    "id": 71,
                    "name": "Renamed Campaign In LinkedIn",
                    "account": advertising,
                    "campaignGroup": "urn:li:sponsoredCampaignGroup:70",
                    "status": "PAUSED",
                    "test": True,
                    "unitCost": {"amount": "5", "currencyCode": "USD"},
                    "dailyBudget": {"amount": "50", "currencyCode": "USD"},
                },
            ],
            "paging": {"total": 1},
        }
        creatives_response = MagicMock(status_code=200)
        creatives_response.json.return_value = {"elements": [], "paging": {"total": 0}}
        mock_request_linkedin.side_effect = [
            groups_response,
            campaigns_response,
            creatives_response,
        ]
        campaign_messages = len(campaign.message_ids)
        group_messages = len(group.message_ids)
        self.SocialAccountLinkedin.action_import_campaigns()
        self.assertEqual(campaign.unit_cost, 99)
        self.assertEqual(campaign.name, "Synced Campaign")
        self.assertEqual(campaign.stage_id.code, "PAUSED")
        self.assertTrue(campaign.linkedin_is_test)
        self.assertTrue(campaign.linkedin_needs_update)
        self.assertEqual(group.total_budget, 500)
        self.assertEqual(group.name, "Synced Group")
        self.assertEqual(group.stage_id.code, "ACTIVE")
        self.assertTrue(group.linkedin_needs_update)
        self.assertEqual(len(campaign.message_ids), campaign_messages + 1)
        self.assertEqual(len(group.message_ids), group_messages + 1)
        mock_request_linkedin.side_effect = None
        mock_request_linkedin.return_value = MagicMock(status_code=204)
        campaign.action_update_linkedin()
        payload = mock_request_linkedin.call_args.kwargs["json_data"]
        self.assertEqual(payload["patch"]["$set"]["unitCost"]["amount"], "99.0")
        self.assertEqual(
            payload["patch"]["$set"]["campaignGroup"],
            "urn:li:sponsoredCampaignGroup:70",
        )
        self.assertFalse(campaign.linkedin_needs_update)
        group.action_update_linkedin()
        payload = mock_request_linkedin.call_args.kwargs["json_data"]
        self.assertEqual(payload["patch"]["$set"]["totalBudget"]["amount"], "500.0")
        self.assertFalse(group.linkedin_needs_update)

    def test_deleted_on_linkedin_history_message(self):
        currency_usd = self.env.ref("base.USD")
        group = self.SocialAdvertisingCampaignGroup.create(
            {
                "name": "History Group",
                "remote_ref": "urn:li:sponsoredCampaignGroup:90",
                "total_budget": 100,
                "currency_id": currency_usd.id,
                "stage_id": self.get_stage_linkedin("group", "ACTIVE").id,
            }
        )
        campaign = self.SocialAdvertisingCampaign.create(
            {
                "name": "History Campaign",
                "campaign_group_id": group.id,
                "media_id": self.media_linkedin_data_id.id,
                "account_ids": [Command.link(self.SocialAccountLinkedin.id)],
                "unit_cost": 1,
                "daily_budget": 10,
                "remote_ref": "urn:li:sponsoredCampaign:91",
                "stage_id": self.get_stage_linkedin("campaign", "ACTIVE").id,
            }
        )
        group_messages = len(group.message_ids)
        campaign_messages = len(campaign.message_ids)
        elements_group = [
            {
                "id": 90,
                "name": "History Group",
                "status": "PENDING_DELETION",
                "totalBudget": {"amount": "100", "currencyCode": "USD"},
            }
        ]
        elements_campaign = [
            {
                "id": 91,
                "name": "History Campaign",
                "status": "REMOVED",
                "campaignGroup": "urn:li:sponsoredCampaignGroup:90",
                "unitCost": {"amount": "1", "currencyCode": "USD"},
                "dailyBudget": {"amount": "10", "currencyCode": "USD"},
            }
        ]
        self.SocialAccountLinkedin._upsert_linkedin_campaigns(
            elements_group, elements_campaign
        )
        self.assertEqual(group.stage_id.code, "PENDING_DELETION")
        self.assertEqual(campaign.stage_id.code, "REMOVED")
        self.assertEqual(len(group.message_ids), group_messages + 1)
        self.assertEqual(len(campaign.message_ids), campaign_messages + 1)
        self.SocialAccountLinkedin._upsert_linkedin_campaigns(
            elements_group, elements_campaign
        )
        self.assertEqual(len(group.message_ids), group_messages + 1)
        self.assertEqual(len(campaign.message_ids), campaign_messages + 1)

    def test_import_campaign_group_without_campaigns_keeps_its_media(self):
        """A group imported empty must still be a LinkedIn group.

        Its media is what enables the LinkedIn buttons, the lock and the
        pending changes flag, and it has no campaign to deduce it from.
        """
        counts = self.SocialAccountLinkedin._upsert_linkedin_campaigns(
            [
                {
                    "id": 120,
                    "name": "Empty Imported Group",
                    "status": "ARCHIVED",
                    "totalBudget": {"amount": "50", "currencyCode": "USD"},
                }
            ],
            [],
        )
        self.assertEqual(counts["groups"], 1)
        group = self.SocialAdvertisingCampaignGroup.search(
            [("remote_ref", "=", "urn:li:sponsoredCampaignGroup:120")]
        )
        self.assertEqual(group.media_id, self.SocialAccountLinkedin.media_id)
        self.assertEqual(group.stage_id.code, "ARCHIVED")
        self.assertTrue(group.linkedin_locked)

    def test_import_keeps_the_local_political_declaration(self):
        """The declaration is a legal choice, so the import must not undo it."""
        group = self.SocialAdvertisingCampaignGroup.create(
            {
                "name": "Political Group",
                "remote_ref": "urn:li:sponsoredCampaignGroup:130",
                "total_budget": 100,
                "currency_id": self.env.ref("base.USD").id,
            }
        )
        campaign = self.SocialAdvertisingCampaign.create(
            {
                "name": "Political Campaign",
                "campaign_group_id": group.id,
                "media_id": self.media_linkedin_data_id.id,
                "account_ids": [Command.link(self.SocialAccountLinkedin.id)],
                "unit_cost": 1,
                "daily_budget": 10,
                "remote_ref": "urn:li:sponsoredCampaign:131",
            }
        )
        campaign.write({"linkedin_political_intent": "POLITICAL"})
        self.assertTrue(campaign.linkedin_needs_update)
        messages = len(campaign.message_ids)
        self.SocialAccountLinkedin._upsert_linkedin_campaigns(
            [
                {
                    "id": 130,
                    "name": "Political Group",
                    "totalBudget": {"amount": "100", "currencyCode": "USD"},
                }
            ],
            [
                {
                    "id": 131,
                    "name": "Political Campaign",
                    "campaignGroup": "urn:li:sponsoredCampaignGroup:130",
                    "politicalIntent": "NOT_POLITICAL",
                    "unitCost": {"amount": "1", "currencyCode": "USD"},
                    "dailyBudget": {"amount": "10", "currencyCode": "USD"},
                }
            ],
        )
        self.assertEqual(campaign.linkedin_political_intent, "POLITICAL")
        self.assertEqual(len(campaign.message_ids), messages + 1)
        self.assertIn(
            "political declaration: Not political advertising",
            campaign.message_ids[0].body,
            msg="The LinkedIn value has to be recoverable from the chatter.",
        )

    def test_upsert_linkedin_campaigns_updates_the_archived_records(self):
        """An archived record still owns its URN: never create it again."""
        currency_usd = self.env.ref("base.USD")
        group = self.SocialAdvertisingCampaignGroup.create(
            {
                "name": "Archived Group",
                "remote_ref": "urn:li:sponsoredCampaignGroup:95",
                "total_budget": 100,
                "currency_id": currency_usd.id,
            }
        )
        campaign = self.SocialAdvertisingCampaign.create(
            {
                "name": "Archived Campaign",
                "campaign_group_id": group.id,
                "media_id": self.media_linkedin_data_id.id,
                "account_ids": [Command.link(self.SocialAccountLinkedin.id)],
                "remote_ref": "urn:li:sponsoredCampaign:96",
            }
        )
        group.write({"active": False})
        campaign.write({"active": False})
        counts = self.SocialAccountLinkedin._upsert_linkedin_campaigns(
            [
                {
                    "id": 95,
                    "name": "Archived Group Renamed",
                    "status": "ACTIVE",
                    "totalBudget": {"amount": "150", "currencyCode": "USD"},
                }
            ],
            [
                {
                    "id": 96,
                    "name": "Archived Campaign Renamed",
                    "status": "ACTIVE",
                    "campaignGroup": "urn:li:sponsoredCampaignGroup:95",
                    "unitCost": {"amount": "2", "currencyCode": "USD"},
                    "dailyBudget": {"amount": "20", "currencyCode": "USD"},
                }
            ],
        )
        self.assertEqual(counts, {"groups": 0, "campaigns": 0})
        self.assertEqual(group.name, "Archived Group Renamed")
        self.assertEqual(group.total_budget, 150)
        self.assertEqual(campaign.name, "Archived Campaign Renamed")
        self.assertEqual(campaign.daily_budget, 20)
        self.assertFalse(group.active)
        self.assertFalse(campaign.active)

    def test_advertising_media_types_contains_linkedin(self):
        self.assertIn("linkedin", self.SocialAccount._advertising_media_types())
        self.assertTrue(self.SocialAccountLinkedin.can_sync_advertising_accounts)

    def test_fetch_advertising_accounts_dedupes_the_roles(self):
        """``adAccountUsers`` answers one row per role of the member."""
        users_response = self.generate_magic_mock(
            **{
                "status_code": 200,
                "json_return_value": {
                    "paging": {"total": 2},
                    "elements": [
                        {"account": "urn:li:sponsoredAccount:1"},
                        {"account": "urn:li:sponsoredAccount:1"},
                    ],
                },
            }
        )
        advertising_account = self.generate_magic_mock(
            **{
                "status_code": 200,
                "json_return_value": {"id": 1, "test": True, "name": "One"},
            }
        )
        patch_request_linkedin = self.generate_patch(
            **{
                "type_object": True,
                "model_patch": self.SocialAccountLinkedin,
                "method_patch": "_request_linkedin",
                "side_effect": [users_response, advertising_account],
            }
        )
        with patch_request_linkedin as mock_request_linkedin:
            values = self.SocialAccountLinkedin._fetch_advertising_accounts()
        self.assertEqual(len(values), 1)
        self.assertEqual(mock_request_linkedin.call_count, 2)

    def test_prepare_advertising_account_without_a_known_currency(self):
        values = self.SocialAccountLinkedin._prepare_linkedin_advertising_account(
            "urn:li:sponsoredAccount:1", {"id": 1, "currency": "XXX"}
        )
        self.assertFalse(values["currency_id"])
        self.assertEqual(values["name"], "1")
        self.assertEqual(values["environment"], "production")

    def test_display_name_shortens_the_linkedin_reference(self):
        """The advertiser only ever sees the identifier, not the whole URN."""
        self.AdvertisingAccountLinkedin.write({"name": "Dunder Mifflin"})
        self.assertEqual(
            self.AdvertisingAccountLinkedin.display_name, "Dunder Mifflin (999)"
        )

    def test_display_name_of_another_media_keeps_the_whole_reference(self):
        """Shortening belongs to the connector of each social media."""
        media = self.env["social.media"].create({"name": "Other media"})
        account = self.SocialAccount.create(
            {"name": "Other account", "media_id": media.id}
        )
        advertising_account = self.env["social.advertising.account"].create(
            {
                "account_id": account.id,
                "name": "Other Ads",
                "remote_ref": "urn:ad:1",
                "environment": "test",
            }
        )
        self.assertEqual(advertising_account.display_name, "Other Ads (urn:ad:1)")

    def test_web_url_points_to_the_campaign_manager(self):
        self.assertEqual(
            self.AdvertisingAccountLinkedin.web_url,
            "https://www.linkedin.com/campaignmanager/accounts/999/",
        )

    def test_action_sync_advertising_accounts_notify(self):
        users_response = self.generate_magic_mock(
            **{
                "status_code": 200,
                "json_return_value": {
                    "paging": {"total": 1},
                    "elements": [{"account": "urn:li:sponsoredAccount:999"}],
                },
            }
        )
        advertising_account = self.generate_magic_mock(
            **{
                "status_code": 200,
                "json_return_value": {"id": 999, "test": True, "name": "Ads"},
            }
        )
        patch_request_linkedin = self.generate_patch(
            **{
                "type_object": True,
                "model_patch": self.SocialAccountLinkedin,
                "method_patch": "_request_linkedin",
                "side_effect": [users_response, advertising_account],
            }
        )
        with patch_request_linkedin:
            res = self.SocialAccountLinkedin.action_sync_advertising_accounts_notify()
        self.assertEqual(res["params"]["type"], "success")
        self.assertEqual(self.AdvertisingAccountLinkedin.name, "Ads")

    def test_action_sync_advertising_accounts_notify_error(self):
        failed_response = self.generate_magic_mock(
            **{"status_code": 403, "json_return_value": {"message": "Unauthorized"}}
        )
        patch_request_linkedin = self.generate_patch(
            **{
                "type_object": True,
                "model_patch": self.SocialAccountLinkedin,
                "method_patch": "_request_linkedin",
                "return_value": failed_response,
            }
        )
        with patch_request_linkedin:
            res = self.SocialAccountLinkedin.action_sync_advertising_accounts_notify()
        self.assertEqual(res["params"]["type"], "danger")
        self.assertIn(
            "The advertising accounts could not be read from LinkedIn",
            res["params"]["message"],
        )

    def _creative_element(self, **values):
        """Return a Creatives API element, the one of the fixtures by default."""
        return dict(
            {
                "id": "urn:li:sponsoredCreative:1",
                "content": {"reference": "urn:li:ugcPost:1"},
                "campaign": "urn:li:sponsoredCampaign:001",
                "createdAt": self.start_timestamp,
                "intendedStatus": "DRAFT",
                "servingHoldReasons": ["UNDER_REVIEW"],
                "isTest": True,
            },
            **values,
        )

    def _patch_fetch_creatives(self, elements):
        return patch(
            PATCH_ADVERTISING_ACCOUNT_LINKEDIN.format("_fetch_linkedin_creatives"),
            autospec=True,
            return_value=elements,
        )

    def _patch_statistics_ads(self, statistics):
        return patch(
            PATCH_ADVERTISING_ACCOUNT_LINKEDIN.format("_get_linkedin_statistics_ads"),
            autospec=True,
            return_value=statistics,
        )

    def test_fetch_linkedin_ads(self):
        """Every value the ad model stores comes from what LinkedIn answered."""
        self.SocialPostAccountCampaignLinkedin.write({"remote_ref": "urn:li:ugcPost:1"})
        statistics = [
            {
                "pivotValues": ["urn:li:sponsoredCreative:1"],
                "impressions": 100,
                "clicks": 10,
                "actionClicks": 2,
                "adUnitClicks": 3,
                "externalWebsiteConversions": 1,
                "costInUsd": "12.5",
            }
        ]
        with self._patch_fetch_creatives(
            [self._creative_element()]
        ), self._patch_statistics_ads(statistics):
            values = self.SocialAccountLinkedin._fetch_linkedin_ads(
                self.start_datetime, self.end_datetime
            )
        self.assertEqual(len(values), 1)
        ad_values = values[0]
        self.assertEqual(ad_values["remote_ref"], "urn:li:sponsoredCreative:1")
        self.assertEqual(
            ad_values["advertising_account_id"], self.AdvertisingAccountLinkedin.id
        )
        self.assertEqual(
            ad_values["campaign_id"], self.SocialAdvertisingCampaignLinkedin.id
        )
        self.assertEqual(
            ad_values["post_account_id"],
            self.SocialPostAccountCampaignLinkedin.id,
            msg="The ad is linked to the publication it promotes.",
        )
        self.assertEqual(
            ad_values["stage_id"], self.get_stage_linkedin("ad", "DRAFT").id
        )
        self.assertEqual(ad_values["status_detail"], "UNDER_REVIEW")
        self.assertEqual(ad_values["impression_count"], 100)
        self.assertEqual(ad_values["click_count"], 10)
        self.assertEqual(ad_values["action_click_count"], 2)
        self.assertEqual(ad_values["ad_unit_click_count"], 3)
        self.assertEqual(ad_values["conversion_count"], 1)
        self.assertEqual(ad_values["cost"], "12.5")
        self.assertEqual(
            ad_values["currency_id"],
            self.env.ref("base.USD").id,
            msg="LinkedIn answers the cost in dollars, whatever the account "
            "is billed in.",
        )
        self.assertEqual(ad_values["statistics_date_from"], self.start_datetime)
        self.assertEqual(ad_values["statistics_date_to"], self.end_datetime)
        self.assertIn("creativeIds", ad_values["url"])

    def test_fetch_linkedin_ads_created_date_is_stored_in_utc(self):
        """The moment is stored in UTC so every user reads it in his own zone."""
        with self._patch_fetch_creatives(
            [self._creative_element()]
        ), self._patch_statistics_ads([]):
            values = self.SocialAccountLinkedin._fetch_linkedin_ads(
                self.start_datetime, self.end_datetime
            )
        created_date = values[0]["created_date"]
        self.assertIsNone(
            created_date.tzinfo,
            msg="The ORM stores naive datetimes.",
        )
        self.assertEqual(created_date, self.start_datetime)

    def test_fetch_linkedin_ads_without_a_known_post(self):
        """A creative promoting an unknown post is kept, without publication."""
        with self._patch_fetch_creatives(
            [self._creative_element(content={"reference": "urn:li:ugcPost:404"})]
        ), self._patch_statistics_ads([]):
            values = self.SocialAccountLinkedin._fetch_linkedin_ads(
                self.start_datetime, self.end_datetime
            )
        self.assertEqual(len(values), 1)
        self.assertFalse(values[0]["post_account_id"])

    def test_fetch_linkedin_ads_without_creatives(self):
        with self._patch_fetch_creatives([]):
            self.assertEqual(
                self.SocialAccountLinkedin._fetch_linkedin_ads(
                    self.start_datetime, self.end_datetime
                ),
                [],
            )

    def test_fetch_ads_keeps_the_hook_signature(self):
        """The framework calls the hook without arguments, as the base does."""
        with self._patch_fetch_creatives(
            [self._creative_element()]
        ), self._patch_statistics_ads([]):
            values = self.SocialAccountLinkedin._fetch_ads()
        self.assertEqual(len(values), 1)
        start_date, end_date = self.SocialAccountLinkedin._get_default_filter_date(
            None, None
        )
        self.assertEqual(values[0]["statistics_date_from"], start_date)
        self.assertEqual(values[0]["statistics_date_to"], end_date)

    def test_fetch_ad_refs(self):
        """The check only lists the creatives, it asks for nothing else."""
        with self._patch_fetch_creatives(
            [self._creative_element()]
        ), self._patch_statistics_ads([]) as mock_statistics:
            refs = self.SocialAccountLinkedin._fetch_ad_refs()
        self.assertEqual(refs, {"urn:li:sponsoredCreative:1"})
        mock_statistics.assert_not_called()

    def test_get_linkedin_statistics_ads_is_asked_for_in_batches(self):
        """A single call with every creative builds a URL the API refuses."""
        ads_ids = [f"urn:li:sponsoredCreative:{index}" for index in range(45)]
        with patch(
            PATCH_ADVERTISING_ACCOUNT_LINKEDIN.format("_get_linkedin_statistics"),
            autospec=True,
            return_value=[],
        ) as mock_get_linkedin_statistics:
            self.SocialAccountLinkedin._get_linkedin_statistics_ads(
                ads_ids, self.start_datetime, self.end_datetime
            )
        self.assertEqual(mock_get_linkedin_statistics.call_count, 3)
        self.assertEqual(
            len(mock_get_linkedin_statistics.call_args_list[0].kwargs["ads_ids"]),
            _CHUNK_SIZE_ANALYTICS_LINKEDIN,
        )


class TestSocialAccountAdsScopesLinkedin(TestSocialCommonAdvertisingLinkedin):
    def test_missing_ads_scopes(self):
        """A token granted before this module says what it lacks."""
        account = self.SocialAccountLinkedin
        account.sudo().linkedin_granted_scopes = "w_member_social, r_ads"
        self.assertEqual(account.linkedin_missing_ads_scopes, "rw_ads, r_ads_reporting")

    def test_missing_ads_scopes_none(self):
        account = self.SocialAccountLinkedin
        account.sudo().linkedin_granted_scopes = (
            "w_member_social, r_ads, rw_ads, r_ads_reporting"
        )
        self.assertFalse(account.linkedin_missing_ads_scopes)

    def test_missing_ads_scopes_unknown(self):
        """An account whose scopes are unknown is not accused of anything."""
        account = self.SocialAccountLinkedin
        account.sudo().linkedin_granted_scopes = False
        self.assertFalse(account.linkedin_missing_ads_scopes)

    def test_post_init_hook_warns_the_concerned_accounts(self):
        account = self.SocialAccountLinkedin
        account.sudo().linkedin_granted_scopes = "w_member_social"
        before = len(account.message_ids)
        post_init_hook(self.env)
        self.assertEqual(len(account.message_ids), before + 1)
        self.assertIn("r_ads", account.message_ids[0].body)

    def test_post_init_hook_leaves_the_authorized_ones_alone(self):
        account = self.SocialAccountLinkedin
        account.sudo().linkedin_granted_scopes = (
            "w_member_social, r_ads, rw_ads, r_ads_reporting"
        )
        before = len(account.message_ids)
        post_init_hook(self.env)
        self.assertEqual(len(account.message_ids), before)
