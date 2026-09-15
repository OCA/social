# Copyright 2026 Binhex <https://www.binhex.cloud>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from unittest.mock import MagicMock, patch

from odoo.exceptions import UserError
from odoo.fields import Command
from odoo.tests.common import tagged

from odoo.addons.social_media_linkedin.tests.test_common_linkedin import (
    PATCH_ACCOUNT_LINKEDIN,
)

from .test_common_advertising_linkedin import (
    PATCH_ADVERTISING_ACCOUNT_LINKEDIN,
    PATCH_ADVERTISING_CAMPAIGN_GROUP_LINKEDIN,
    TestSocialCommonAdvertisingLinkedin,
)


@tagged("post_install", "-at_install")
class TestSocialAdvertisingCampaignGroupLinkedin(TestSocialCommonAdvertisingLinkedin):
    def test_get_linkedin_account(self):
        """The account is taken from the campaigns before the fallback."""
        self.assertEqual(
            self.SocialAdvertisingCampaignGroupLinkedin._get_linkedin_account(),
            self.SocialAccountLinkedin,
        )

    def test_get_linkedin_account_without_campaigns(self):
        """Without campaigns the fallback only works with a single account."""
        group = self.SocialAdvertisingCampaignGroup.create({"name": "Standalone Group"})
        accounts = self.SocialAccount.search([("media_type", "=", "linkedin")])
        self.assertGreater(len(accounts), 1)
        with self.assertRaises(
            UserError, msg="Guessing the advertiser is never acceptable."
        ):
            group._get_linkedin_account()
        (accounts - self.SocialAccountLinkedin).write({"active": False})
        self.assertEqual(group._get_linkedin_account(), self.SocialAccountLinkedin)

    def test_get_linkedin_account_with_several_campaign_accounts(self):
        self.SocialAdvertisingCampaign.create(
            {
                "name": "Campaign of another advertiser",
                "campaign_group_id": self.SocialAdvertisingCampaignGroupLinkedin.id,
                "media_id": self.media_linkedin_data_id.id,
                "account_ids": [Command.link(self.SocialAccountLinkedinData.id)],
            }
        )
        with self.assertRaises(UserError):
            self.SocialAdvertisingCampaignGroupLinkedin._get_linkedin_account()

    def test_check_total_budget_exactly_covering_the_daily_budgets(self):
        """The budgets are compared with the rounding of their currency.

        Three daily budgets of ``0.1`` add up to ``0.30000000000000004`` as
        floats, so a total budget of ``0.3`` looks exceeded to a plain
        comparison while it is not.
        """
        group = self.SocialAdvertisingCampaignGroup.create(
            {
                "name": "Rounding Group",
                "total_budget": 0.3,
                "currency_id": self.env.ref("base.USD").id,
            }
        )
        for index in range(3):
            self.SocialAdvertisingCampaign.create(
                {
                    "name": f"Rounding Campaign {index}",
                    "campaign_group_id": group.id,
                    "daily_budget": 0.1,
                }
            )
        self.assertEqual(len(group.campaign_ids), 3)

    def test_check_total_budget_without_a_currency(self):
        """The currency is optional, and the rule works without it."""
        group = self.SocialAdvertisingCampaignGroup.create(
            {"name": "Currencyless Group", "total_budget": 100}
        )
        self.SocialAdvertisingCampaign.create(
            {
                "name": "Currencyless Campaign",
                "campaign_group_id": group.id,
                "daily_budget": 50,
            }
        )
        group.with_context(skip_linkedin_needs_update=True).total_budget = 80
        self.assertFalse(group.currency_id)
        self.assertEqual(group.total_budget, 80)

    @patch(PATCH_ACCOUNT_LINKEDIN.format("_request_linkedin"))
    @patch(
        PATCH_ADVERTISING_ACCOUNT_LINKEDIN.format("_get_linkedin_advertising_account")
    )
    def test_group_publish_linkedin(self, mock_advertising, mock_request_linkedin):
        mock_advertising.return_value = "urn:li:sponsoredAccount:999"
        group = self.SocialAdvertisingCampaignGroup.create(
            {
                "name": "Standalone Group",
                "total_budget": 100,
                "currency_id": self.env.ref("base.USD").id,
            }
        )
        self.SocialAdvertisingCampaign.create(
            {
                "name": "Campaign of the standalone group",
                "campaign_group_id": group.id,
                "media_id": self.media_linkedin_data_id.id,
                "account_ids": [Command.link(self.SocialAccountLinkedin.id)],
            }
        )
        mock_request_linkedin.return_value = MagicMock(
            status_code=201,
            headers={"x-restli-id": "555"},
        )
        group.action_publish_linkedin()
        self.assertEqual(group.remote_ref, "urn:li:sponsoredCampaignGroup:555")
        self.assertEqual(group.stage_id.code, "DRAFT")
        self.assertFalse(group.linkedin_needs_update)
        payload = mock_request_linkedin.call_args.kwargs["json_data"]
        self.assertEqual(payload["status"], "DRAFT")
        self.assertEqual(payload["totalBudget"]["amount"], "100.0")
        with self.assertRaises(UserError):
            group.action_publish_linkedin()
        empty_group = self.SocialAdvertisingCampaignGroup.create(
            {"name": "Empty Group"}
        )
        with self.assertRaises(UserError):
            empty_group.action_publish_linkedin()

    def test_currency_change_flags_the_pending_changes(self):
        """The currency is pushed to LinkedIn, so it is a synchronized field."""
        group = self.SocialAdvertisingCampaignGroupLinkedin
        self.assertFalse(group.linkedin_needs_update)
        group.write({"currency_id": self.env.ref("base.EUR").id})
        self.assertTrue(group.linkedin_needs_update)

    def test_group_archive_linkedin(self):
        group = self.SocialAdvertisingCampaignGroupLinkedin
        messages = len(group.message_ids)
        with self._mock_linkedin(
            MagicMock(status_code=204), self.SocialAccountLinkedin
        ) as mock_request:
            group.action_archive_linkedin()
        self.assertEqual(group.stage_id.code, "ARCHIVED")
        self.assertTrue(group.linkedin_locked)
        self.assertFalse(group.linkedin_needs_update)
        self.assertEqual(len(group.message_ids), messages + 1)
        self.assertEqual(
            mock_request.call_args.kwargs["json_data"],
            {"patch": {"$set": {"status": "ARCHIVED"}}},
        )
        self.assertEqual(
            mock_request.call_args.kwargs["endpoint"],
            "/adAccounts/999/adCampaignGroups/456",
        )
        with self.assertRaises(
            UserError, msg="An archived campaign group is read only on LinkedIn."
        ):
            group.action_archive_linkedin()

    def test_group_archive_linkedin_errors(self):
        group = self.SocialAdvertisingCampaignGroup.create(
            {
                "name": "Group Without Urn",
                "total_budget": 100,
                "currency_id": self.env.ref("base.USD").id,
            }
        )
        self.SocialAdvertisingCampaign.create(
            {
                "name": "Campaign of the group",
                "campaign_group_id": group.id,
                "media_id": self.media_linkedin_data_id.id,
                "account_ids": [Command.link(self.SocialAccountLinkedin.id)],
            }
        )
        with self.assertRaises(UserError):
            group.action_archive_linkedin()
        group.write({"remote_ref": "urn:li:sponsoredCampaignGroup:457"})
        with patch(
            PATCH_ADVERTISING_CAMPAIGN_GROUP_LINKEDIN.format("_get_linkedin_account"),
            autospec=True,
            return_value=self.env["social.account"],
        ):
            with self.assertRaises(UserError):
                group.action_archive_linkedin()
        error_response = MagicMock(status_code=400)
        error_response.json.return_value = {"message": "Cannot archive"}
        with self._mock_linkedin(error_response, self.SocialAccountLinkedin):
            with self.assertRaises(UserError):
                group.action_archive_linkedin()
        self.assertNotEqual(group.stage_id.code, "ARCHIVED")

    def test_web_url_points_to_the_group_in_the_campaign_manager(self):
        group = self.SocialAdvertisingCampaignGroupLinkedin
        group.advertising_account_id = self.AdvertisingAccountLinkedin
        self.assertEqual(
            group.web_url,
            "https://www.linkedin.com/campaignmanager/accounts/999/"
            "campaign-groups?campaignGroupIds=%5B%27456%27%5D",
        )

    def test_web_url_is_empty_without_an_advertising_account(self):
        """Nothing to build the address from means no button at all."""
        self.assertFalse(self.SocialAdvertisingCampaignGroupLinkedin.web_url)

    def test_runschedule_is_refreshed_only_for_a_draft(self):
        """A group already running keeps the dates LinkedIn accepts."""
        group = self.SocialAdvertisingCampaignGroupLinkedin
        self.assertFalse(group._linkedin_runschedule_values())
        group.stage_id = self.get_stage_linkedin("group", "DRAFT")
        values = group._linkedin_runschedule_values()
        self.assertGreater(values["runSchedule"]["end"], values["runSchedule"]["start"])

    def test_group_publish_linkedin_without_an_account(self):
        """The advertising account is never guessed, so there is nothing to do."""
        group = self.SocialAdvertisingCampaignGroup.create(
            {
                "name": "Accountless Group",
                "total_budget": 100,
                "currency_id": self.env.ref("base.USD").id,
            }
        )
        with patch(
            PATCH_ADVERTISING_CAMPAIGN_GROUP_LINKEDIN.format("_get_linkedin_account"),
            autospec=True,
            return_value=self.env["social.account"],
        ):
            with self.assertRaises(UserError) as error:
                group.action_publish_linkedin()
        self.assertIn("available to create the group", str(error.exception))

    def test_group_update_linkedin_errors(self):
        group = self.SocialAdvertisingCampaignGroup.create({"name": "Group To Update"})
        self.SocialAdvertisingCampaign.create(
            {
                "name": "Campaign of the group to update",
                "campaign_group_id": group.id,
                "media_id": self.media_linkedin_data_id.id,
                "account_ids": [Command.link(self.SocialAccountLinkedin.id)],
            }
        )
        with self.assertRaises(UserError) as error:
            group.action_update_linkedin()
        self.assertIn("does not exist on LinkedIn yet", str(error.exception))
        group.write({"remote_ref": "urn:li:sponsoredCampaignGroup:458"})
        with self.assertRaises(UserError) as error:
            group.action_update_linkedin()
        self.assertIn("must have a currency", str(error.exception))
        group.write({"currency_id": self.env.ref("base.USD").id, "total_budget": 100})
        with patch(
            PATCH_ADVERTISING_CAMPAIGN_GROUP_LINKEDIN.format("_get_linkedin_account"),
            autospec=True,
            return_value=self.env["social.account"],
        ):
            with self.assertRaises(UserError) as error:
                group.action_update_linkedin()
        self.assertIn("available to update the group", str(error.exception))
        error_response = MagicMock(status_code=400)
        error_response.json.return_value = {"message": "Cannot update"}
        with self._mock_linkedin(error_response, self.SocialAccountLinkedin):
            with self.assertRaises(UserError) as error:
                group.action_update_linkedin()
        self.assertIn("could not be updated on LinkedIn", str(error.exception))
        self.assertTrue(group.linkedin_needs_update)

    def test_group_update_linkedin(self):
        """A successful update clears the pending changes and says so."""
        group = self.SocialAdvertisingCampaignGroupLinkedin
        group.write({"total_budget": 20000})
        self.assertTrue(group.linkedin_needs_update)
        messages = len(group.message_ids)
        with self._mock_linkedin(
            MagicMock(status_code=204), self.SocialAccountLinkedin
        ) as mock_request:
            group.action_update_linkedin()
        self.assertFalse(group.linkedin_needs_update)
        self.assertEqual(len(group.message_ids), messages + 1)
        values = mock_request.call_args.kwargs["json_data"]["patch"]["$set"]
        self.assertEqual(values["totalBudget"]["amount"], "20000.0")
        self.assertEqual(
            mock_request.call_args.kwargs["endpoint"],
            "/adAccounts/999/adCampaignGroups/456",
        )
