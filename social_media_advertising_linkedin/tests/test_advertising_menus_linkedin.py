# Copyright 2026 Binhex <https://www.binhex.cloud>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo.tools.safe_eval import safe_eval

from .test_common_advertising_linkedin import TestSocialCommonAdvertisingLinkedin

MODULE = "social_media_advertising_linkedin"


class TestAdvertisingMenusLinkedin(TestSocialCommonAdvertisingLinkedin):
    """The advertising lists of LinkedIn hang from their own menu.

    Campaign groups, campaigns, ads and stages belong to a single social
    media, so every connector contributes its own submenu filtered on it
    instead of sharing a list where all the social medias are mixed.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.media_other = cls.env["social.media"].create({"name": "Other media"})
        cls.AdLinkedin = cls.env["social.advertising.ad"].create(
            {
                "name": "LinkedIn ad",
                "remote_ref": "urn:li:sponsoredCreative:001",
                "account_id": cls.SocialAccountLinkedin.id,
                "advertising_account_id": cls.AdvertisingAccountLinkedin.id,
                "campaign_id": cls.SocialAdvertisingCampaignLinkedin.id,
            }
        )

    def test_menus_hang_under_the_linkedin_menu(self):
        """The four advertising lists are children of the LinkedIn menu."""
        menu = self.env.ref(f"{MODULE}.social_advertising_linkedin_menu")
        self.assertEqual(
            menu.parent_id,
            self.env.ref("social_media_advertising.social_advertising_menu"),
        )
        self.assertFalse(menu.action)
        self.assertEqual(
            menu.child_id.mapped("name"),
            ["Advertising accounts", "Campaign Groups", "Campaigns", "Ads"],
        )
        self.assertEqual(menu.child_id.mapped("sequence"), [10, 20, 30, 40])
        group_user = self.env.ref("social_media_base.group_social_media_user")
        for child in menu.child_id:
            self.assertIn(group_user, child.groups_id)

    def test_stage_menu_hangs_under_the_stages_menu(self):
        """The LinkedIn stages are a child of the generic Stages menu."""
        menu = self.env.ref(f"{MODULE}.social_stage_linkedin_menu")
        self.assertEqual(
            menu.parent_id,
            self.env.ref("social_media_advertising.social_stage_root_menu"),
        )
        self.assertIn(
            self.env.ref("social_media_base.group_social_media_manager"),
            menu.groups_id,
        )

    def test_actions_are_filtered_on_linkedin(self):
        """Every action of the submenu only answers the LinkedIn records."""
        for xml_id in (
            "social_advertising_account_linkedin_action",
            "social_advertising_campaign_group_linkedin_action",
            "social_advertising_campaign_linkedin_action",
            "social_advertising_ad_linkedin_action",
            "social_stage_linkedin_action",
        ):
            action = self.env.ref(f"{MODULE}.{xml_id}")
            domain = safe_eval(action.domain)
            self.assertEqual(domain, [("media_id.media_type", "=", "linkedin")])
            records = self.env[action.res_model].search(domain)
            self.assertTrue(records)
            self.assertNotIn("other", records.mapped("media_id.media_type"))

    def test_campaign_action_excludes_another_media(self):
        """A campaign of another social media is out of the LinkedIn list."""
        action = self.env.ref(f"{MODULE}.social_advertising_campaign_linkedin_action")
        campaign_other = self.SocialAdvertisingCampaign.create(
            {"name": "Campaign of another media", "media_id": self.media_other.id}
        )
        campaigns = self.SocialAdvertisingCampaign.search(safe_eval(action.domain))
        self.assertIn(self.SocialAdvertisingCampaignLinkedin, campaigns)
        self.assertNotIn(campaign_other, campaigns)

    def test_action_context_defaults_the_media(self):
        """Creating from the submenu already sets the social media."""
        action = self.env.ref(f"{MODULE}.social_advertising_campaign_linkedin_action")
        campaign = self.SocialAdvertisingCampaign.with_context(
            **safe_eval(action.context)
        ).create({"name": "Campaign from the menu"})
        self.assertEqual(campaign.media_id, self.media_linkedin_data_id)

        action = self.env.ref(
            f"{MODULE}.social_advertising_campaign_group_linkedin_action"
        )
        group = self.SocialAdvertisingCampaignGroup.with_context(
            **safe_eval(action.context)
        ).create({"name": "Group from the menu"})
        self.assertEqual(group.media_id, self.media_linkedin_data_id)

        action = self.env.ref(f"{MODULE}.social_stage_linkedin_action")
        stage = self.SocialStage.with_context(**safe_eval(action.context)).create(
            {"name": "Stage from the menu", "code": "TEST_CODE"}
        )
        self.assertEqual(stage.media_id, self.media_linkedin_data_id)

    def test_ad_action_keeps_the_kanban_and_the_search_view(self):
        """The filtered list of ads is the generic one, only narrowed."""
        action = self.env.ref(f"{MODULE}.social_advertising_ad_linkedin_action")
        self.assertEqual(action.view_mode, "kanban,tree,form")
        self.assertEqual(
            action.search_view_id,
            self.env.ref("social_media_advertising.social_advertising_ad_view_search"),
        )

    def test_advertising_ad_action_answers_per_media(self):
        """A deleted LinkedIn ad falls back to the LinkedIn list."""
        Ad = self.env["social.advertising.ad"]
        self.assertEqual(
            Ad._advertising_ad_action("linkedin")["xml_id"],
            f"{MODULE}.social_advertising_ad_linkedin_action",
        )
        self.assertEqual(
            Ad._advertising_ad_action()["xml_id"],
            "social_media_advertising.social_advertising_ad_action",
        )
