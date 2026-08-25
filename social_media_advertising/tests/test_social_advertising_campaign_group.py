# Copyright 2026 Binhex <https://www.binhex.cloud>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import psycopg2

from odoo.tools import mute_logger

from .test_social_advertising_common import TestSocialAdvertisingCommon


class TestSocialAdvertisingCampaignGroup(TestSocialAdvertisingCommon):
    def test_compute_campaign_count(self):
        empty_group = self.SocialAdvertisingCampaignGroup.create(
            {"name": "Empty group"}
        )
        self.assertEqual(empty_group.campaign_count, 0)
        self.assertEqual(self.campaign_group_id.campaign_count, 1)
        self.SocialAdvertisingCampaign.create(
            {
                "name": "Second campaign",
                "campaign_group_id": self.campaign_group_id.id,
            }
        )
        self.campaign_group_id.invalidate_recordset()
        self.assertEqual(self.campaign_group_id.campaign_count, 2)

    def test_compute_campaign_count_ignores_archived_campaigns(self):
        self.campaign_id.write({"active": False})
        self.campaign_group_id.invalidate_recordset()
        self.assertEqual(self.campaign_group_id.campaign_count, 0)

    def test_media_id_follows_the_only_media_of_its_campaigns(self):
        self.campaign_id.write({"media_id": self.social_media_id.id})
        self.assertEqual(self.campaign_group_id.media_id, self.social_media_id)

    def test_media_id_is_reset_by_campaigns_of_mixed_medias(self):
        other_media = self.SocialMedia.create({"name": "Other media"})
        self.campaign_id.write({"media_id": self.social_media_id.id})
        self.SocialAdvertisingCampaign.create(
            {
                "name": "Other media campaign",
                "campaign_group_id": self.campaign_group_id.id,
                "media_id": other_media.id,
            }
        )
        self.assertFalse(self.campaign_group_id.media_id)

    def test_media_id_set_by_hand_survives_a_recompute(self):
        """An empty group keeps the media a connector wrote on it."""
        group = self.SocialAdvertisingCampaignGroup.create(
            {"name": "Empty group", "media_id": self.social_media_id.id}
        )
        self.SocialAdvertisingCampaign.create(
            {"name": "Campaign without media", "campaign_group_id": group.id}
        )
        group.invalidate_recordset()
        self.assertEqual(group.media_id, self.social_media_id)

    def test_action_view_campaigns(self):
        action = self.campaign_group_id.action_view_campaigns()
        self.assertEqual(action["res_model"], "social.advertising.campaign")
        self.assertEqual(action["view_mode"], "tree,form")
        self.assertEqual(
            action["domain"], [("campaign_group_id", "=", self.campaign_group_id.id)]
        )
        self.assertEqual(
            action["context"]["default_campaign_group_id"], self.campaign_group_id.id
        )

    def test_remote_ref_is_not_copied(self):
        self.campaign_group_id.write({"remote_ref": "urn:remote:group:1"})
        self.assertFalse(self.campaign_group_id.copy().remote_ref)

    def test_stage_id_is_not_copied(self):
        stage = self.SocialStage.create(
            {
                "name": "Active",
                "code": "ACTIVE",
                "media_id": self.social_media_id.id,
                "applies_to": "group",
            }
        )
        self.campaign_group_id.write({"stage_id": stage.id})
        self.assertFalse(self.campaign_group_id.copy().stage_id)

    @mute_logger("odoo.sql_db")
    def test_remote_ref_is_unique_per_media(self):
        """The reference of the social media names a single campaign group.

        ``media_id`` has to be written: PostgreSQL does not consider a
        unique index violated by two NULL values.
        """
        values = {
            "name": "Imported group",
            "remote_ref": "urn:remote:group:1",
            "media_id": self.social_media_id.id,
        }
        self.SocialAdvertisingCampaignGroup.create(values)
        with self.assertRaises(psycopg2.IntegrityError):
            with self.env.cr.savepoint():
                self.SocialAdvertisingCampaignGroup.create(values)

    def test_archived_group_is_hidden_from_the_default_search(self):
        self.campaign_group_id.write({"active": False})
        self.assertNotIn(
            self.campaign_group_id, self.SocialAdvertisingCampaignGroup.search([])
        )
        self.assertIn(
            self.campaign_group_id,
            self.SocialAdvertisingCampaignGroup.with_context(active_test=False).search(
                []
            ),
        )
