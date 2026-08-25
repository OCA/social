# Copyright 2026 Binhex <https://www.binhex.cloud>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from unittest.mock import MagicMock, patch

from odoo.exceptions import UserError
from odoo.fields import Command

from odoo.addons.social_media_linkedin.tests.test_common_linkedin import (
    PATCH_ACCOUNT_LINKEDIN,
)

from .test_common_advertising_linkedin import (
    PATCH_ADVERTISING_ACCOUNT_LINKEDIN,
    PATCH_ADVERTISING_CAMPAIGN_GROUP_LINKEDIN,
    TestSocialCommonAdvertisingLinkedin,
)


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
            headers={"Location": "/adAccounts/999/adCampaignGroups/555"},
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
