# Copyright 2025 Binhex <https://www.binhex.cloud>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).


from unittest.mock import patch

from odoo.fields import Command
from odoo.tools import hmac

from odoo.addons.mail.tests.common import mail_new_test_user
from odoo.addons.social_media_base.tests.test_social_common import (
    TestSocialMediaBaseCommon,
)

PATCH_WIZARD_LINKEDIN = "odoo.addons.social_media_linkedin.wizards.{}"
PATCH_WIZARD_ACCOUNT_LINKEDIN = PATCH_WIZARD_LINKEDIN.format("wizard_social_account.{}")

PATCH_ACCOUNT_LINKEDIN = (
    "odoo.addons.social_media_linkedin.models.social_account.SocialAccount.{}"
)
PATCH_POST_ACCOUNT_LINKEDIN = (
    "odoo.addons.social_media_linkedin.models.social_post_account.SocialPostAccount.{}"
)
PATCH_CONTROLLER_LINKEDIN = (
    "odoo.addons.social_media_linkedin.controllers."
    "social_media_linkedin.SocialMediaLinkedin.{}"
)


class TestSocialCommonLinkedin(TestSocialMediaBaseCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.VALID_PNG_B64 = (
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVQYV2NgYGBgAAAA"
            "BAABJzQnCgAAAABJRU5ErkJggg=="
        )
        cls.WizardAccount = cls.env["wizard.social.account"]
        cls.wizard_account_id = cls.WizardAccount.create(
            {
                "media_id": cls.env.ref(
                    "social_media_linkedin.social_media_linkedin"
                ).id,
                "csrf_state_token": "fake-csrf-token",
                "linkedin_client": "fake-client-id",
                "linkedin_secret": "fake-secret",
            }
        )
        cls.url_callback = f"{cls.wizard_account_id.get_base_url()}/linkedin/callback"
        cls.media_linkedin_id = cls.SocialMedia.create(
            {
                "name": "linkedin",
                "media_type": "linkedin",
            }
        )

        cls.SocialAccountLinkedin = cls.SocialAccount.create(
            {
                "name": "Linkedin Account",
                "media_id": cls.media_linkedin_id.id,
                "linkedin_account_urn": "urn:li:organization:123456",
                "access_token": "fake-token",
                "linkedin_client_id": "fake-client-id",
                "linkedin_secret": "fake-secret",
            }
        )

        cls.SocialAccountLinkedinData = cls.SocialAccount.create(
            {
                "name": "Linkedin Account",
                "media_id": cls.env.ref(
                    "social_media_linkedin.social_media_linkedin"
                ).id,
                "linkedin_account_urn": "urn:li:organization:123456890",
                "access_token": "fake-token",
            }
        )

        cls.SocialPostLinkedin = cls.SocialPost.create(
            {
                "message": "Test Message",
                "account_ids": [Command.set(cls.SocialAccountLinkedin.ids)],
            }
        )

        post_account = {
            "message": "Test Message",
            "account_id": cls.SocialAccountLinkedin.id,
            "media_id": cls.media_linkedin_id.id,
            "post_id": cls.SocialPostLinkedin.id,
            "linkedin_post_account_urn": "1234567890",
            "state": "posted",
        }

        cls.SocialPostAccountLinkedin = cls.SocialPostAccount.create(post_account)

        post_account.update(
            {
                "state": "ready",
                "linkedin_post_account_urn": False,
            }
        )
        cls.SocialPostAccountReadyLinkedin = cls.SocialPostAccount.create(post_account)

        cls.SocialCampaignGroupLinkedin = cls.UtmGroupCampaign.create(
            {
                "name": "Campaign Group 1",
                "linkedin_urn": "urn:li:sponsoredCampaignGroup:456",
                "total_budget": 10000,
                "currency_id": cls.env.ref("base.USD").id,
            }
        )

        cls.SocialCampaignLinkedin = cls.UtmCampaign.create(
            {
                "name": "Campaign 1",
                "campaign_group_id": cls.SocialCampaignGroupLinkedin.id,
                "currency_id": cls.SocialCampaignGroupLinkedin.currency_id.id,
                "linkedin_urn": "urn:li:sponsoredCampaign:001",
                "media_id": cls.media_linkedin_id.id,
            }
        )

        cls.SocialCampaignLinkedin2 = cls.UtmCampaign.create(
            {
                "name": "Campaign 2",
                "campaign_group_id": cls.SocialCampaignGroupLinkedin.id,
                "currency_id": cls.SocialCampaignGroupLinkedin.currency_id.id,
                "linkedin_urn": "urn:li:sponsoredCampaign:002",
            }
        )

        cls.SocialPostCampaignLinkedin = cls.SocialPost.create(
            {
                "message": "Test Message for Campaign",
                "account_ids": [Command.set(cls.SocialAccountLinkedin.ids)],
                "campaign_id": cls.SocialCampaignLinkedin.id,
            }
        )
        values = {
            "message": "Test Message for Campaign",
            "account_id": cls.SocialAccountLinkedin.id,
            "media_id": cls.media_linkedin_id.id,
            "post_id": cls.SocialPostCampaignLinkedin.id,
        }
        cls.SocialPostAccountCampaignLinkedin = cls.SocialPostAccount.create(values)
        cls.admin_media_linkedin = mail_new_test_user(
            cls.env,
            groups="base.group_user,base.group_system",
            login="admin_media_linkedin",
            name="Admin Media Linkedin",
            signature="--\nMEDIAX",
        )

    def generate_code(self, code_generated="fake-code-token"):
        return hmac(
            self.env(su=True),
            f"{self.media_linkedin_id.media_type}-account-{code_generated}-csrf-token",
            self.media_linkedin_id.id,
        )

    def get_patch_exceptions_linkedin(self, fake_client=False, side_effect=False):
        if side_effect:
            return patch.object(
                type(self.SocialAccountLinkedin),
                "_request_linkedin",
                autospec=True,
                side_effect=side_effect,
            )
        return patch.object(
            type(self.SocialAccountLinkedin),
            "_request_linkedin",
            autospec=True,
            return_value=fake_client,
        )
