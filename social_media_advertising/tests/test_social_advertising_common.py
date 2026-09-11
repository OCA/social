# Copyright 2026 Binhex <https://www.binhex.cloud>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import Command

from odoo.addons.social_media_base.tests.test_social_common import (
    TestSocialMediaBaseCommon,
)

PATCH_ADVERTISING_MODELS = "odoo.addons.social_media_advertising.models"
PATCH_ADVERTISING_ACCOUNT = "{}.social_account.SocialAccount.{}".format(
    PATCH_ADVERTISING_MODELS, "{}"
)
PATCH_ADVERTISING_CAMPAIGN = (
    "{}.social_advertising_campaign.SocialAdvertisingCampaign.{}".format(
        PATCH_ADVERTISING_MODELS, "{}"
    )
)


class TestSocialAdvertisingCommon(TestSocialMediaBaseCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.User = cls.env["res.users"]
        cls.SocialAdvertisingAccount = cls.env["social.advertising.account"]
        cls.SocialAdvertisingCampaign = cls.env["social.advertising.campaign"]
        cls.SocialAdvertisingCampaignGroup = cls.env[
            "social.advertising.campaign.group"
        ]
        cls.SocialStage = cls.env["social.stage"]
        cls.SocialTag = cls.env["social.tag"]
        cls.campaign_group_id = cls.SocialAdvertisingCampaignGroup.create(
            {"name": "Test Group"}
        )
        cls.campaign_id = cls.SocialAdvertisingCampaign.create(
            {
                "name": "Test Campaign",
                "campaign_group_id": cls.campaign_group_id.id,
                "account_ids": [Command.set([cls.social_account_id.id])],
            }
        )

    @classmethod
    def _create_advertising_account(cls, account=None, **values):
        """Return an advertising account of ``account``, test one by default.

        A ``classmethod`` so that ``setUpClass`` can build its fixture with
        it instead of repeating the values.
        """
        account = account or cls.social_account_id
        return cls.SocialAdvertisingAccount.create(
            dict(
                {
                    "account_id": account.id,
                    "name": "Advertising account",
                    "remote_ref": "urn:ad:test",
                    "environment": account.environment,
                },
                **values,
            )
        )

    def _create_social_media_user(self, login="advertising_user_test"):
        return self.User.create(
            {
                "name": "Social user",
                "login": login,
                "groups_id": [
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

    def _create_social_media_manager(self, login="advertising_manager_test"):
        return self.User.create(
            {
                "name": "Social manager",
                "login": login,
                "groups_id": [
                    Command.set(
                        [
                            self.env.ref("base.group_user").id,
                            self.env.ref(
                                "social_media_base.group_social_media_manager"
                            ).id,
                        ]
                    )
                ],
            }
        )
