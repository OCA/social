# Copyright 2026 Binhex <https://www.binhex.cloud>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from unittest.mock import MagicMock, patch

from odoo.exceptions import UserError, ValidationError
from odoo.fields import Command

from odoo.addons.social_media_linkedin.tests.test_common_linkedin import (
    PATCH_ACCOUNT_LINKEDIN,
)

from .test_common_advertising_linkedin import (
    PATCH_ADVERTISING_ACCOUNT_LINKEDIN,
    PATCH_ADVERTISING_LINKEDIN,
    TestSocialCommonAdvertisingLinkedin,
)

ADVERTISING_ACCOUNT_URN = "urn:li:sponsoredAccount:999"


class TestSocialAdvertisingCampaignLinkedin(TestSocialCommonAdvertisingLinkedin):
    def test_compute_media_id(self):
        campaign = self.SocialAdvertisingCampaign.create(
            {
                "name": "Test Campaign",
                "account_ids": [Command.link(self.SocialAccountLinkedin.id)],
                "campaign_group_id": self.SocialAdvertisingCampaignGroupLinkedin.id,
            }
        )
        self.assertIn(self.SocialAccountLinkedin.media_id, campaign.allow_media_ids)

    def test_check_linkedin_single_account(self):
        """A LinkedIn campaign refuses a second LinkedIn account."""
        second_account = self.SocialAccountLinkedin.copy(
            {"name": "Second LinkedIn account", "remote_ref": "urn:li:organization:2"}
        )
        with self.assertRaises(ValidationError):
            self.SocialAdvertisingCampaignLinkedin.account_ids = [
                Command.link(second_account.id)
            ]

    def test_validate_publish_linkedin_video_objective(self):
        """LinkedIn requires an objective to create a video campaign."""
        campaign = self.SocialAdvertisingCampaignLinkedin
        campaign.write(
            {
                "linkedin_format": "SINGLE_VIDEO",
                "linkedin_objective": False,
                "unit_cost": 2,
                "daily_budget": 20,
            }
        )
        with self.assertRaises(UserError) as context:
            campaign._validate_publish_linkedin()
        self.assertIn("requires an objective", str(context.exception))

        campaign.linkedin_objective = "VIDEO_VIEW"
        campaign._validate_publish_linkedin()

    def test_linkedin_create_campaign_sends_format(self):
        """The ad format travels to LinkedIn, which fixes it on creation."""
        campaign = self.SocialAdvertisingCampaignLinkedin
        campaign.linkedin_format = "SINGLE_VIDEO"
        campaign.linkedin_objective = "VIDEO_VIEW"
        response = MagicMock(status_code=201)
        response.headers = {"Location": "/adAccounts/999/adCampaigns/321"}
        patch_request_linkedin = self.get_patch_exceptions_linkedin(response)
        with patch_request_linkedin as mock_request_linkedin:
            res = campaign._linkedin_create_campaign(
                self.SocialAccountLinkedin,
                "urn:li:sponsoredAccount:999",
                "urn:li:sponsoredCampaignGroup:456",
            )
        self.assertEqual(res, "urn:li:sponsoredCampaign:321")
        self.assertEqual(campaign.stage_id.code, "DRAFT")
        json_data = mock_request_linkedin.call_args.kwargs["json_data"]
        self.assertEqual(json_data["format"], "SINGLE_VIDEO")
        self.assertEqual(json_data["objectiveType"], "VIDEO_VIEW")

    def test_check_daily_budget(self):
        with self.assertRaises(ValidationError):
            self.SocialAdvertisingCampaignLinkedin.daily_budget = 5000
            self.SocialAdvertisingCampaignLinkedin2.daily_budget = 5001

    def test_check_daily_budget_without_a_total_budget(self):
        """A group without total budget sets no limit, as on LinkedIn."""
        self.SocialAdvertisingCampaignGroupLinkedin.with_context(
            skip_linkedin_needs_update=True
        ).total_budget = 0
        self.SocialAdvertisingCampaignLinkedin.daily_budget = 5000
        self.SocialAdvertisingCampaignLinkedin2.daily_budget = 5001
        self.assertEqual(self.SocialAdvertisingCampaignLinkedin2.daily_budget, 5001)

    def test_check_daily_budget_skipped_on_import(self):
        """The import is never stopped by the local budget rule."""
        self.SocialAdvertisingCampaignLinkedin.with_context(
            skip_linkedin_budget_check=True
        ).write({"daily_budget": 5000})
        self.SocialAdvertisingCampaignLinkedin2.with_context(
            skip_linkedin_budget_check=True
        ).write({"daily_budget": 5001})
        self.assertEqual(self.SocialAdvertisingCampaignLinkedin2.daily_budget, 5001)

    def test_check_daily_budget_lowering_the_total_budget(self):
        """The rule is watched from the group side too."""
        self.SocialAdvertisingCampaignLinkedin.daily_budget = 6000
        with self.assertRaises(ValidationError):
            self.SocialAdvertisingCampaignGroupLinkedin.with_context(
                skip_linkedin_needs_update=True
            ).total_budget = 5000

    def test_check_daily_budget_moving_the_campaign_to_another_group(self):
        small_group = self.SocialAdvertisingCampaignGroup.create(
            {
                "name": "Small Group",
                "total_budget": 50,
                "currency_id": self.env.ref("base.USD").id,
            }
        )
        self.SocialAdvertisingCampaignLinkedin.daily_budget = 100
        with self.assertRaises(ValidationError):
            self.SocialAdvertisingCampaignLinkedin.with_context(
                skip_linkedin_needs_update=True
            ).campaign_group_id = small_group

    def test_linkedin_lock_covers_the_media(self):
        """Taking the campaign out of LinkedIn used to escape the lock."""
        campaign = self.SocialAdvertisingCampaignLinkedin
        campaign.with_context(
            skip_linkedin_needs_update=True
        ).stage_id = self.get_stage_linkedin("campaign", "ARCHIVED")
        self.assertTrue(campaign.linkedin_locked)
        with self.assertRaises(UserError):
            campaign.media_id = False

    def test_action_publish_linkedin_validation(self):
        group = self.SocialAdvertisingCampaignGroup.create({"name": "Test Group"})
        campaign = self.SocialAdvertisingCampaign.create(
            {
                "name": "Test Campaign",
                "campaign_group_id": group.id,
                "media_id": self.media_linkedin_data_id.id,
                "account_ids": [Command.link(self.SocialAccountLinkedin.id)],
            }
        )
        with self.assertRaises(UserError) as context:
            campaign.action_publish_linkedin()
        self.assertIn("total budget must be positive", str(context.exception))
        self.assertIn("unit cost must be positive", str(context.exception))
        self.assertIn("daily budget must be positive", str(context.exception))

    @patch(PATCH_ACCOUNT_LINKEDIN.format("_request_linkedin"))
    @patch(
        PATCH_ADVERTISING_ACCOUNT_LINKEDIN.format("_get_linkedin_advertising_account")
    )
    def test_action_publish_linkedin(
        self, mock_advertising_account, mock_request_linkedin
    ):
        currency = self.env.ref("base.USD")
        group = self.SocialAdvertisingCampaignGroup.create(
            {"name": "Test Group", "total_budget": 100, "currency_id": currency.id}
        )
        campaign = self.SocialAdvertisingCampaign.create(
            {
                "name": "Test Campaign",
                "campaign_group_id": group.id,
                "media_id": self.media_linkedin_data_id.id,
                "account_ids": [Command.link(self.SocialAccountLinkedin.id)],
                "unit_cost": 1,
                "daily_budget": 10,
            }
        )
        mock_advertising_account.return_value = "urn:li:sponsoredAccount:999"
        mock_request_linkedin.side_effect = [
            MagicMock(
                status_code=201,
                headers={"Location": "/adAccounts/999/adCampaignGroups/45"},
            ),
            MagicMock(
                status_code=201, headers={"Location": "/adAccounts/999/adCampaigns/67"}
            ),
        ]
        campaign.action_publish_linkedin()
        self.assertEqual(
            campaign.campaign_group_id.remote_ref,
            "urn:li:sponsoredCampaignGroup:45",
        )
        self.assertEqual(campaign.remote_ref, "urn:li:sponsoredCampaign:67")
        self.assertEqual(campaign.stage_id.code, "DRAFT")
        self.assertEqual(campaign.campaign_group_id.stage_id.code, "DRAFT")
        for call in mock_request_linkedin.call_args_list:
            self.assertEqual(call.kwargs["json_data"]["status"], "DRAFT")

    def test_campaign_locked_linkedin_statuses(self):
        currency_usd = self.env.ref("base.USD")
        group = self.SocialAdvertisingCampaignGroup.create(
            {
                "name": "Locked Group",
                "remote_ref": "urn:li:sponsoredCampaignGroup:80",
                "total_budget": 100,
                "currency_id": currency_usd.id,
            }
        )
        campaign = self.SocialAdvertisingCampaign.create(
            {
                "name": "Locked Campaign",
                "campaign_group_id": group.id,
                "media_id": self.media_linkedin_data_id.id,
                "account_ids": [Command.link(self.SocialAccountLinkedin.id)],
                "unit_cost": 1,
                "daily_budget": 10,
                "remote_ref": "urn:li:sponsoredCampaign:81",
            }
        )
        campaign.stage_id = self.get_stage_linkedin("campaign", "CANCELED")
        group.stage_id = self.get_stage_linkedin("group", "PENDING_DELETION")
        with self.assertRaises(UserError):
            campaign.write({"unit_cost": 5})
        with self.assertRaises(UserError):
            campaign.action_update_linkedin()
        with self.assertRaises(UserError):
            group.write({"total_budget": 200})
        with self.assertRaises(UserError):
            group.action_update_linkedin()
        campaign.with_context(skip_linkedin_needs_update=True).write({"unit_cost": 5})
        group.with_context(skip_linkedin_needs_update=True).write({"total_budget": 200})
        self.assertEqual(campaign.unit_cost, 5)
        self.assertEqual(group.total_budget, 200)
        campaign.stage_id = self.get_stage_linkedin("campaign", "PAUSED")
        campaign.write({"unit_cost": 7})
        self.assertTrue(campaign.linkedin_needs_update)

    def test_campaign_archive_linkedin_draft_group(self):
        """LinkedIn refuses to archive a campaign of a draft group."""
        campaign = self.SocialAdvertisingCampaignLinkedin
        campaign.campaign_group_id.stage_id = self.get_stage_linkedin("group", "DRAFT")
        with self.get_patch_exceptions_linkedin() as mock_request:
            with self.assertRaises(UserError) as error:
                campaign.action_archive_linkedin()
        self.assertIn("still in draft status", str(error.exception))
        mock_request.assert_not_called()

    def test_campaign_archive_linkedin_refreshes_the_schedule(self):
        """A draft campaign travels with a new schedule LinkedIn accepts.

        Its stored start date is the one given on creation, which LinkedIn
        rejects as soon as it belongs to the past.
        """
        campaign = self.SocialAdvertisingCampaignLinkedin
        campaign.stage_id = self.get_stage_linkedin("campaign", "DRAFT")
        with self._mock_linkedin(
            MagicMock(status_code=204), self.SocialAccountLinkedin
        ) as mock_request:
            campaign.action_archive_linkedin()
        values = mock_request.call_args.kwargs["json_data"]["patch"]["$set"]
        self.assertEqual(values["status"], "ARCHIVED")
        self.assertGreater(values["runSchedule"]["start"], 0)
        self.assertGreater(values["runSchedule"]["end"], values["runSchedule"]["start"])
        self.assertEqual(campaign.stage_id.code, "ARCHIVED")

    def test_campaign_archive_linkedin(self):
        campaign = self.SocialAdvertisingCampaignLinkedin
        messages = len(campaign.message_ids)
        with self._mock_linkedin(
            MagicMock(status_code=204), self.SocialAccountLinkedin
        ) as mock_request:
            campaign.action_archive_linkedin()
        self.assertEqual(campaign.stage_id.code, "ARCHIVED")
        self.assertTrue(campaign.linkedin_locked)
        self.assertFalse(campaign.linkedin_needs_update)
        self.assertEqual(len(campaign.message_ids), messages + 1)
        self.assertEqual(
            mock_request.call_args.kwargs["json_data"],
            {"patch": {"$set": {"status": "ARCHIVED"}}},
        )
        self.assertEqual(
            mock_request.call_args.kwargs["endpoint"], "/adAccounts/999/adCampaigns/001"
        )
        with self.assertRaises(
            UserError, msg="An archived campaign is read only on LinkedIn."
        ):
            campaign.action_archive_linkedin()

    def test_campaign_archive_linkedin_errors(self):
        campaign = self.SocialAdvertisingCampaign.create(
            {
                "name": "Campaign Without Urn",
                "campaign_group_id": self.SocialAdvertisingCampaignGroupLinkedin.id,
                "media_id": self.media_linkedin_data_id.id,
                "account_ids": [Command.link(self.SocialAccountLinkedin.id)],
            }
        )
        with self.assertRaises(UserError):
            campaign.action_archive_linkedin()
        campaign.write({"remote_ref": "urn:li:sponsoredCampaign:003"})
        campaign.account_ids = [Command.clear()]
        with self.assertRaises(UserError):
            campaign.action_archive_linkedin()
        campaign.account_ids = [Command.link(self.SocialAccountLinkedin.id)]
        error_response = MagicMock(status_code=400)
        error_response.json.return_value = {"message": "Cannot archive"}
        with self._mock_linkedin(error_response, self.SocialAccountLinkedin):
            with self.assertRaises(UserError):
                campaign.action_archive_linkedin()
        self.assertNotEqual(campaign.stage_id.code, "ARCHIVED")

    def test_archived_stage_locks_writes(self):
        """A campaign archived on LinkedIn refuses local sync changes."""
        campaign = self.SocialAdvertisingCampaignLinkedin
        campaign.stage_id = self.get_stage_linkedin("campaign", "ARCHIVED")
        self.assertTrue(campaign.linkedin_locked)
        with self.assertRaises(UserError):
            campaign.write({"name": "Renamed"})

    def test_publish_campaign_group_without_advertising_account(self):
        """Without an advertising account nothing is sent to LinkedIn."""
        with self.get_patch_exceptions_linkedin() as mock_request:
            self.assertFalse(
                self.SocialAdvertisingCampaignLinkedin._linkedin_publish_campaign_group(
                    self.SocialAccountLinkedin, False
                )
            )
            mock_request.assert_not_called()

    def test_publish_campaign_group_already_created(self):
        """An existing group is only verified, never created again."""
        with self.get_patch_exceptions_linkedin(
            MagicMock(status_code=200)
        ) as mock_request:
            urn = (
                self.SocialAdvertisingCampaignLinkedin._linkedin_publish_campaign_group(
                    self.SocialAccountLinkedin, ADVERTISING_ACCOUNT_URN
                )
            )
        self.assertEqual(urn, self.SocialAdvertisingCampaignGroupLinkedin.remote_ref)
        mock_request.assert_called_once()

    def test_publish_campaign_group_creates_the_missing_one(self):
        """A URN unknown to LinkedIn is replaced by a newly created group."""
        patch_request = self.get_patch_exceptions_linkedin(
            side_effect=[
                MagicMock(status_code=404),
                MagicMock(
                    status_code=201,
                    headers={"Location": "/adAccounts/999/adCampaignGroups/456"},
                ),
            ]
        )
        with patch(
            PATCH_ADVERTISING_LINKEDIN.format(
                "social_advertising_campaign_group.run_schedule_window_linkedin"
            ),
            autospec=True,
            return_value=(111111, 222222),
        ), patch_request as mock_request:
            urn = (
                self.SocialAdvertisingCampaignLinkedin._linkedin_publish_campaign_group(
                    self.SocialAccountLinkedin, ADVERTISING_ACCOUNT_URN
                )
            )
        self.assertEqual(urn, "urn:li:sponsoredCampaignGroup:456")
        self.assertEqual(
            self.SocialAdvertisingCampaignGroupLinkedin.remote_ref,
            "urn:li:sponsoredCampaignGroup:456",
        )
        self.assertEqual(mock_request.call_count, 2)
        self.assertEqual(
            mock_request.call_args.kwargs["json_data"]["runSchedule"],
            {"start": 111111, "end": 222222},
            msg="The group is created with a schedule built at the moment of "
            "the call, or LinkedIn answers DATE_TOO_EARLY.",
        )

    def test_publish_campaign_group_creation_error(self):
        """The creation error of the group is reported to the user."""
        patch_request = self.get_patch_exceptions_linkedin(
            side_effect=[
                MagicMock(status_code=404),
                MagicMock(status_code=400, headers={"error": "Invalid request"}),
            ]
        )
        with patch_request as mock_request:
            with self.assertRaises(UserError) as error:
                self.SocialAdvertisingCampaignLinkedin._linkedin_publish_campaign_group(
                    self.SocialAccountLinkedin, ADVERTISING_ACCOUNT_URN
                )
        self.assertIn(
            "The campaign group could not be created on LinkedIn",
            str(error.exception),
        )
        self.assertEqual(mock_request.call_count, 2)

    def test_validate_publish_linkedin_political_intent(self):
        """LinkedIn requires the political advertising declaration."""
        campaign = self.SocialAdvertisingCampaignLinkedin
        campaign.write(
            {
                "linkedin_political_intent": False,
                "unit_cost": 2,
                "daily_budget": 20,
            }
        )
        with self.assertRaises(UserError) as context:
            campaign._validate_publish_linkedin()
        self.assertIn("political advertising", str(context.exception))

        campaign.linkedin_political_intent = "NOT_POLITICAL"
        campaign._validate_publish_linkedin()

    def test_linkedin_create_campaign_sends_political_intent(self):
        """The declaration travels to LinkedIn, which rejects it otherwise."""
        campaign = self.SocialAdvertisingCampaignLinkedin
        self.assertEqual(campaign.linkedin_political_intent, "NOT_POLITICAL")
        response = MagicMock(status_code=201)
        response.headers = {"Location": "/adAccounts/999/adCampaigns/321"}
        with self.get_patch_exceptions_linkedin(response) as mock_request_linkedin:
            campaign._linkedin_create_campaign(
                self.SocialAccountLinkedin,
                ADVERTISING_ACCOUNT_URN,
                "urn:li:sponsoredCampaignGroup:456",
            )
        json_data = mock_request_linkedin.call_args.kwargs["json_data"]
        self.assertEqual(json_data["politicalIntent"], "NOT_POLITICAL")

    def test_action_update_linkedin_sends_political_intent(self):
        """A local change of the declaration is pushed to LinkedIn."""
        campaign = self.SocialAdvertisingCampaignLinkedin
        campaign.linkedin_political_intent = "POLITICAL"
        self.assertTrue(campaign.linkedin_needs_update)
        with self._mock_linkedin(
            MagicMock(status_code=204), self.SocialAccountLinkedin
        ) as mock_request:
            campaign.action_update_linkedin()
        values = mock_request.call_args.kwargs["json_data"]["patch"]["$set"]
        self.assertEqual(values["politicalIntent"], "POLITICAL")
        self.assertFalse(campaign.linkedin_needs_update)

    @patch(PATCH_ACCOUNT_LINKEDIN.format("_request_linkedin"))
    @patch(
        PATCH_ADVERTISING_ACCOUNT_LINKEDIN.format("_get_linkedin_advertising_account")
    )
    def test_action_publish_linkedin_keeps_the_group_reference(
        self, mock_advertising_account, mock_request_linkedin
    ):
        """A campaign failure must not lose the group created on LinkedIn.

        LinkedIn cannot delete a campaign group, so its reference has to
        survive the failure or the next import would duplicate it.
        """
        currency = self.env.ref("base.USD")
        group = self.SocialAdvertisingCampaignGroup.create(
            {"name": "Test Group", "total_budget": 100, "currency_id": currency.id}
        )
        campaign = self.SocialAdvertisingCampaign.create(
            {
                "name": "Test Campaign",
                "campaign_group_id": group.id,
                "media_id": self.media_linkedin_data_id.id,
                "account_ids": [Command.link(self.SocialAccountLinkedin.id)],
                "unit_cost": 1,
                "daily_budget": 10,
            }
        )
        mock_advertising_account.return_value = ADVERTISING_ACCOUNT_URN
        error_response = MagicMock(status_code=400)
        error_response.json.return_value = {"message": "Invalid campaign"}
        mock_request_linkedin.side_effect = [
            MagicMock(
                status_code=201,
                headers={"Location": "/adAccounts/999/adCampaignGroups/45"},
            ),
            error_response,
        ]
        messages = len(campaign.message_ids)
        action = campaign.action_publish_linkedin()
        self.assertEqual(action["params"]["type"], "danger")
        self.assertIn(
            "The campaign could not be created on LinkedIn",
            action["params"]["message"],
        )
        self.assertEqual(len(campaign.message_ids), messages + 1)
        self.assertEqual(group.remote_ref, "urn:li:sponsoredCampaignGroup:45")
        self.assertEqual(group.stage_id.code, "DRAFT")
        self.assertFalse(campaign.remote_ref)

    def test_publish_campaign_group_verification_error(self):
        """An unexpected answer while verifying the group is reported too."""
        patch_request = self.get_patch_exceptions_linkedin(
            side_effect=[MagicMock(status_code=400)]
        )
        with patch_request as mock_request:
            with self.assertRaises(UserError) as error:
                self.SocialAdvertisingCampaignLinkedin._linkedin_publish_campaign_group(
                    self.SocialAccountLinkedin, ADVERTISING_ACCOUNT_URN
                )
        self.assertIn(
            "The campaign group could not be checked on LinkedIn",
            str(error.exception),
        )
        mock_request.assert_called_once()
