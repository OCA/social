# Copyright 2026 Binhex <https://www.binhex.cloud>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from unittest.mock import patch

import psycopg2

from odoo import Command
from odoo.exceptions import AccessError
from odoo.tests import tagged
from odoo.tools import mute_logger

from .test_social_advertising_common import (
    PATCH_ADVERTISING_CAMPAIGN,
    TestSocialAdvertisingCommon,
)


class TestSocialAdvertisingCampaign(TestSocialAdvertisingCommon):
    def test_default_user_id_is_the_current_user(self):
        campaign = self.SocialAdvertisingCampaign.create(
            {"name": "Default responsible"}
        )
        self.assertEqual(campaign.user_id, self.env.user)

    def test_compute_display_name_without_media(self):
        self.assertEqual(self.campaign_id.display_name, "Test Campaign")

    def test_compute_display_name_with_media(self):
        field = self.env["social.media"]._fields["media_type"]
        with patch.object(field, "selection", new=[("linkedin", "Linkedin")]):
            self.social_media_id.write({"media_type": "linkedin"})
            self.campaign_id.write({"media_id": self.social_media_id.id})
            self.campaign_id.invalidate_recordset()
            self.assertEqual(self.campaign_id.display_name, "[LINKEDIN] Test Campaign")

    def test_compute_display_name_without_name(self):
        """A campaign being created shows no media prefix on its own."""
        field = self.env["social.media"]._fields["media_type"]
        with patch.object(field, "selection", new=[("linkedin", "Linkedin")]):
            self.social_media_id.write({"media_type": "linkedin"})
            campaign = self.SocialAdvertisingCampaign.new(
                {"media_id": self.social_media_id.id}
            )
            self.assertFalse(campaign.display_name)

    def test_available_campaign_is_empty_without_a_connector(self):
        """This module offers no media type: every one comes from a connector.

        The implementation of this module is reached on its own, so an
        installed connector appending its own type does not hide a
        regression here.
        """
        generic = next(
            parent
            for parent in type(self.campaign_id).mro()
            if parent.__module__.startswith(
                "odoo.addons.social_media_advertising.models"
            )
        )
        self.assertEqual(generic._available_campaign(self.campaign_id), [])

    def test_compute_allow_media_ids_excludes_media_without_connector(self):
        """The fixture media has no ``media_type``, so no connector can offer
        it and it must never be part of the allowed medias."""
        self.assertNotIn(self.social_media_id, self.campaign_id.allow_media_ids)

    def test_compute_allow_media_ids_with_connector(self):
        field = self.env["social.media"]._fields["media_type"]
        with patch.object(field, "selection", new=[("linkedin", "Linkedin")]):
            self.social_media_id.write({"media_type": "linkedin"})
            with patch(
                PATCH_ADVERTISING_CAMPAIGN.format("_available_campaign"),
                autospec=True,
                return_value=["linkedin"],
            ):
                self.campaign_id.invalidate_recordset()
                self.assertIn(self.social_media_id, self.campaign_id.allow_media_ids)

    def test_account_ids_accepts_several_accounts(self):
        other_account = self.SocialAccount.create(
            {"name": "Other account", "media_id": self.social_media_id.id}
        )
        self.campaign_id.write({"account_ids": [Command.link(other_account.id)]})
        self.assertEqual(len(self.campaign_id.account_ids), 2)

    def test_tag_ids(self):
        tag = self.SocialTag.create({"name": "Promo"})
        self.campaign_id.write({"tag_ids": [Command.link(tag.id)]})
        self.assertEqual(self.campaign_id.tag_ids, tag)

    def test_remote_ref_is_not_copied(self):
        self.campaign_id.write({"remote_ref": "urn:remote:campaign:1"})
        self.assertFalse(self.campaign_id.copy().remote_ref)

    def test_stage_id_is_not_copied(self):
        stage = self.SocialStage.create(
            {
                "name": "Active",
                "code": "ACTIVE",
                "media_id": self.social_media_id.id,
            }
        )
        self.campaign_id.write({"stage_id": stage.id})
        self.assertFalse(self.campaign_id.copy().stage_id)

    @mute_logger("odoo.sql_db")
    def test_remote_ref_is_unique_per_media(self):
        """The reference of the social media names a single campaign.

        ``media_id`` has to be written: PostgreSQL does not consider a
        unique index violated by two NULL values.
        """
        values = {
            "name": "Imported campaign",
            "remote_ref": "urn:remote:campaign:1",
            "media_id": self.social_media_id.id,
        }
        self.SocialAdvertisingCampaign.create(values)
        with self.assertRaises(psycopg2.IntegrityError):
            with self.env.cr.savepoint():
                self.SocialAdvertisingCampaign.create(values)


@tagged("post_install", "-at_install")
class TestSocialAdvertisingCampaignSecurity(TestSocialAdvertisingCommon):
    """Record rules and access rights of the campaigns and the stages.

    Users are created here, so every module has to be in the registry.
    """

    def test_rule_user_sees_only_his_own_campaigns(self):
        social_user = self._create_social_media_user()
        other_campaign = self.SocialAdvertisingCampaign.create(
            {"name": "Someone else campaign", "user_id": self.env.user.id}
        )
        own_campaign = self.SocialAdvertisingCampaign.with_user(social_user).create(
            {"name": "Own campaign"}
        )
        self.assertEqual(own_campaign.user_id, social_user)
        visible = self.SocialAdvertisingCampaign.with_user(social_user).search([])
        self.assertIn(own_campaign, visible)
        self.assertNotIn(other_campaign, visible)
        with self.assertRaises(AccessError):
            other_campaign.with_user(social_user).read(["name"])

    def test_rule_manager_sees_every_campaign(self):
        manager = self._create_social_media_manager()
        visible = self.SocialAdvertisingCampaign.with_user(manager).search([])
        self.assertIn(self.campaign_id, visible)

    def test_user_cannot_unlink_a_stage(self):
        social_user = self._create_social_media_user()
        stage = self.SocialStage.create(
            {
                "name": "Active",
                "code": "ACTIVE",
                "media_id": self.social_media_id.id,
            }
        )
        with self.assertRaises(AccessError):
            stage.with_user(social_user).unlink()
