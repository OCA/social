# Copyright 2026 Binhex <https://www.binhex.cloud>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from unittest.mock import patch

from odoo.exceptions import UserError
from odoo.tests.common import Form

from .test_social_advertising_common import TestSocialAdvertisingCommon


class TestSocialPostAdvertising(TestSocialAdvertisingCommon):
    def test_social_campaign_id_follows_the_parent_post(self):
        self.social_post_id.social_campaign_id = self.campaign_id
        self.assertEqual(
            self.social_post_account_id.social_campaign_id, self.campaign_id
        )
        self.social_post_id.social_campaign_id = False
        self.assertFalse(self.social_post_account_id.social_campaign_id)

    def test_the_social_campaign_of_an_imported_publication_is_kept(self):
        """A publication without parent post keeps the campaign written on it."""
        imported = self.SocialPostAccount.create(
            {
                "account_id": self.social_account_id.id,
                "message": "Imported from the wall",
                "remote_ref": "urn:remote:1",
            }
        )
        imported.social_campaign_id = self.campaign_id
        imported.write({"like_count": 5})
        imported.invalidate_recordset()
        self.assertEqual(imported.social_campaign_id, self.campaign_id)

    def test_get_allow_social_campaign_domain_filters_on_the_post_media(self):
        """A synthetic media type keeps the test meaningful with a connector
        installed: connectors AND their own clauses to the domain, so only
        the presence of the media clause is asserted, not the whole domain."""
        field = self.env["social.media"]._fields["media_type"]
        with patch.object(field, "selection", new=[("faketype", "Fake type")]):
            self.social_media_id.write({"media_type": "faketype"})
            domain = self.social_post_id._get_allow_social_campaign_domain()
            self.assertIn(("media_id.media_type", "in", ["faketype"]), domain)

    def test_compute_allow_social_campaign_ids_matches_the_post_media(self):
        field = self.env["social.media"]._fields["media_type"]
        other_media = self.SocialMedia.create({"name": "Other media"})
        with patch.object(
            field, "selection", new=[("faketype", "Fake type"), ("otherfake", "Other")]
        ):
            self.social_media_id.write({"media_type": "faketype"})
            other_media.write({"media_type": "otherfake"})
            self.campaign_id.write({"media_id": self.social_media_id.id})
            other_campaign = self.SocialAdvertisingCampaign.create(
                {"name": "Other media campaign", "media_id": other_media.id}
            )
            self.social_post_id.invalidate_recordset()
            allowed = self.social_post_id.allow_social_campaign_ids
            self.assertIn(self.campaign_id, allowed)
            self.assertNotIn(other_campaign, allowed)

    def test_allow_social_campaign_ids_recomputes_on_account_change(self):
        field = self.env["social.media"]._fields["media_type"]
        other_media = self.SocialMedia.create({"name": "Other media"})
        with patch.object(
            field, "selection", new=[("faketype", "Fake type"), ("otherfake", "Other")]
        ):
            self.social_media_id.write({"media_type": "faketype"})
            other_media.write({"media_type": "otherfake"})
            self.campaign_id.write({"media_id": self.social_media_id.id})
            other_account = self.SocialAccount.create(
                {"name": "Other account", "media_id": other_media.id}
            )
            self.social_post_id.write({"account_ids": [(6, 0, [other_account.id])]})
            self.assertNotIn(
                self.campaign_id, self.social_post_id.allow_social_campaign_ids
            )

    def test_onchange_clears_a_campaign_out_of_the_allowed_ones(self):
        """A campaign the post no longer accepts is dropped in the form."""
        field = self.env["social.media"]._fields["media_type"]
        other_media = self.SocialMedia.create({"name": "Other media"})
        with patch.object(
            field, "selection", new=[("faketype", "Fake type"), ("otherfake", "Other")]
        ):
            self.social_media_id.write({"media_type": "faketype"})
            other_media.write({"media_type": "otherfake"})
            self.campaign_id.write({"media_id": self.social_media_id.id})
            self.social_post_id.write({"social_campaign_id": self.campaign_id.id})
            other_account = self.SocialAccount.create(
                {"name": "Other account", "media_id": other_media.id}
            )
            form = Form(self.social_post_id)
            self.assertEqual(form.social_campaign_id, self.campaign_id)
            form.account_ids.add(other_account)
            form.account_ids.remove(id=self.social_account_id.id)
            self.assertFalse(form.social_campaign_id)

    def test_get_locked_content_fields_freezes_the_social_campaign(self):
        locked_fields = self.social_post_id._get_locked_content_fields()
        self.assertIn("social_campaign_id", locked_fields)

    def test_the_social_campaign_of_a_published_post_cannot_be_changed(self):
        self.social_post_account_id.write(
            {"state": "posted", "remote_ref": "urn:posted"}
        )
        self.assertTrue(self.social_post_id.content_locked)
        with self.assertRaises(UserError):
            self.social_post_id.write({"social_campaign_id": self.campaign_id.id})
        self.assertFalse(self.social_post_id.social_campaign_id)

    def test_action_campaign_post_is_a_noop_by_default(self):
        self.assertIsNone(
            self.social_post_account_id._action_campaign_post(self.social_post_id)
        )
