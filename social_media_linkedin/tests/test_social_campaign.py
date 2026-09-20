# Copyright 2025 Binhex <https://www.binhex.cloud>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).


from odoo.addons.social_media_linkedin.tests.test_common_linkedin import (
    TestSocialCommonLinkedin,
)


class TestSocialCampaign(TestSocialCommonLinkedin):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.campaign_group_id = cls.UtmGroupCampaign.create(
            {"name": "Test Group Campaign"}
        )

    def test_compute_media_id(self):
        self.campaign_id = self.UtmCampaign.create(
            {
                "name": "Test Campaign",
                "account_id": self.SocialAccountLinkedin.id,
                "campaign_group_id": self.campaign_group_id.id,
            }
        )
        self.assertIn(
            self.SocialAccountLinkedin.media_id, self.campaign_id.allow_media_ids
        )
