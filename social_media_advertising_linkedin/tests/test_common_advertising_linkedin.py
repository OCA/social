# Copyright 2026 Binhex <https://www.binhex.cloud>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo.fields import Command

from odoo.addons.social_media_linkedin.tests.test_common_linkedin import (
    TestSocialCommonLinkedin,
)

PATCH_ADVERTISING_LINKEDIN = "odoo.addons.social_media_advertising_linkedin.models.{}"
PATCH_ADVERTISING_ACCOUNT_LINKEDIN = PATCH_ADVERTISING_LINKEDIN.format(
    "social_account.SocialAccount.{}"
)
PATCH_ADVERTISING_CAMPAIGN_GROUP_LINKEDIN = PATCH_ADVERTISING_LINKEDIN.format(
    "social_advertising_campaign_group.SocialAdvertisingCampaignGroup.{}"
)


class TestSocialCommonAdvertisingLinkedin(TestSocialCommonLinkedin):
    """Advertising fixtures shared by the LinkedIn connector tests.

    The campaigns are linked to the ``social.media`` record shipped as data
    by ``social_media_linkedin`` because the LinkedIn stages of
    ``social_media_advertising_linkedin`` belong to it, and the domain of
    ``stage_id`` requires the campaign and the stage to share the media.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.SocialAdvertisingCampaign = cls.env["social.advertising.campaign"]
        cls.SocialAdvertisingCampaignGroup = cls.env[
            "social.advertising.campaign.group"
        ]
        cls.SocialStage = cls.env["social.stage"]
        cls.media_linkedin_data_id = cls.env.ref(
            "social_media_linkedin.social_media_linkedin"
        )
        cls.AdvertisingAccountLinkedin = cls.env["social.advertising.account"].create(
            {
                "account_id": cls.SocialAccountLinkedin.id,
                "name": "LinkedIn Ads",
                "remote_ref": "urn:li:sponsoredAccount:999",
                "environment": "test",
                "is_current": True,
            }
        )

        cls.SocialAdvertisingCampaignGroupLinkedin = (
            cls.SocialAdvertisingCampaignGroup.create(
                {
                    "name": "Campaign Group 1",
                    "remote_ref": "urn:li:sponsoredCampaignGroup:456",
                    "total_budget": 10000,
                    "currency_id": cls.env.ref("base.USD").id,
                }
            )
        )

        cls.SocialAdvertisingCampaignLinkedin = cls.SocialAdvertisingCampaign.create(
            {
                "name": "Campaign 1",
                "campaign_group_id": cls.SocialAdvertisingCampaignGroupLinkedin.id,
                "remote_ref": "urn:li:sponsoredCampaign:001",
                "media_id": cls.media_linkedin_data_id.id,
                "account_ids": [Command.link(cls.SocialAccountLinkedin.id)],
            }
        )

        cls.SocialAdvertisingCampaignLinkedin2 = cls.SocialAdvertisingCampaign.create(
            {
                "name": "Campaign 2",
                "campaign_group_id": cls.SocialAdvertisingCampaignGroupLinkedin.id,
                "remote_ref": "urn:li:sponsoredCampaign:002",
            }
        )

        cls.SocialPostCampaignLinkedin = cls.SocialPost.create(
            {
                "message": "Test Message for Campaign",
                "account_ids": [Command.set(cls.SocialAccountLinkedin.ids)],
                "social_campaign_id": cls.SocialAdvertisingCampaignLinkedin.id,
            }
        )
        cls.SocialPostAccountCampaignLinkedin = cls.SocialPostAccount.create(
            {
                "message": "Test Message for Campaign",
                "account_id": cls.SocialAccountLinkedin.id,
                "media_id": cls.media_linkedin_id.id,
                "post_id": cls.SocialPostCampaignLinkedin.id,
            }
        )

    def get_stage_linkedin(self, applies_to, code):
        """Shortcut to the LinkedIn stage of a scope and code."""
        return self.SocialStage._get_stage("linkedin", applies_to, code)
