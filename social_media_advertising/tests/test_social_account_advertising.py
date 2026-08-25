# Copyright 2026 Binhex <https://www.binhex.cloud>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from unittest.mock import patch

from odoo import Command

from .test_social_advertising_common import (
    PATCH_ADVERTISING_ACCOUNT,
    TestSocialAdvertisingCommon,
)


class TestSocialAccountAdvertising(TestSocialAdvertisingCommon):
    def test_advertising_account_urn_follows_the_current_one(self):
        advertising_account = self._create_advertising_account(remote_ref="urn:ad:1")
        advertising_account.action_set_current()
        self.social_account_id.invalidate_recordset()
        self.assertEqual(self.social_account_id.advertising_account_urn, "urn:ad:1")

    def test_environment_change_clears_the_advertising_account(self):
        """The advertising account is resolved per environment."""
        advertising_account = self._create_advertising_account(remote_ref="urn:ad:1")
        advertising_account.action_set_current()
        self.social_account_id.write({"environment": "production"})
        self.assertFalse(advertising_account.is_current)
        self.assertFalse(self.social_account_id.advertising_account_urn)

    def test_can_sync_advertising_accounts_without_a_connector(self):
        self.assertFalse(self.social_account_id.can_sync_advertising_accounts)

    def test_can_sync_advertising_accounts_with_a_connector(self):
        with patch(
            PATCH_ADVERTISING_ACCOUNT.format("_advertising_media_types"),
            autospec=True,
            return_value=[self.social_account_id.media_type],
        ):
            self.social_account_id.invalidate_recordset()
            self.assertTrue(self.social_account_id.can_sync_advertising_accounts)

    def test_action_import_campaigns_default(self):
        res = self.social_account_id.action_import_campaigns()
        self.assertFalse(res["success"])
        self.assertEqual(res["groups"], 0)
        self.assertEqual(res["campaigns"], 0)
        self.assertEqual(res["ads"], 0)

    def test_action_import_campaigns_notify_without_connector(self):
        res = self.social_account_id.action_import_campaigns_notify()
        self.assertEqual(res["tag"], "display_notification")
        self.assertEqual(res["params"]["type"], "danger")
        self.assertEqual(
            res["params"]["next"],
            {"type": "ir.actions.client", "tag": "soft_reload"},
            msg="The view is reloaded so the campaign counters are up to date.",
        )

    def test_action_import_campaigns_notify_success(self):
        with patch(
            PATCH_ADVERTISING_ACCOUNT.format("action_import_campaigns"),
            autospec=True,
            return_value={"success": True, "message": "Imported"},
        ):
            res = self.social_account_id.action_import_campaigns_notify()
            self.assertEqual(res["params"]["type"], "success")
            self.assertEqual(res["params"]["message"], "Imported")

    def test_archive_account_cascades_to_campaigns(self):
        self.social_account_id.write({"active": False})
        self.assertFalse(self.campaign_id.active)
        self.assertFalse(self.campaign_group_id.active)
        self.social_account_id.write({"active": True})
        self.assertTrue(self.campaign_id.active)
        self.assertTrue(self.campaign_group_id.active)

    def test_archive_account_keeps_a_shared_campaign(self):
        """A campaign is only archived when its whole audience is archived."""
        other_account = self.SocialAccount.create(
            {"name": "Other account", "media_id": self.social_media_id.id}
        )
        self.campaign_id.write({"account_ids": [Command.link(other_account.id)]})
        self.social_account_id.write({"active": False})
        self.assertTrue(self.campaign_id.active)
        self.assertTrue(self.campaign_group_id.active)

    def test_archive_shared_campaign_accounts_one_by_one(self):
        """What decides is the state of the accounts, not the current batch."""
        other_account = self.SocialAccount.create(
            {"name": "Other account", "media_id": self.social_media_id.id}
        )
        self.campaign_id.write({"account_ids": [Command.link(other_account.id)]})
        self.social_account_id.write({"active": False})
        self.assertTrue(self.campaign_id.active)
        other_account.write({"active": False})
        self.assertFalse(self.campaign_id.active)
        self.assertFalse(self.campaign_group_id.active)

    def test_archive_account_keeps_a_group_with_another_active_campaign(self):
        other_account = self.SocialAccount.create(
            {"name": "Other account", "media_id": self.social_media_id.id}
        )
        self.SocialAdvertisingCampaign.create(
            {
                "name": "Other campaign",
                "campaign_group_id": self.campaign_group_id.id,
                "account_ids": [Command.set([other_account.id])],
            }
        )
        self.social_account_id.write({"active": False})
        self.assertFalse(self.campaign_id.active)
        self.assertTrue(self.campaign_group_id.active)

    def test_archive_account_cascades_to_a_group_without_campaigns(self):
        """An empty group is only reachable from its advertising account.

        Groups imported from the social media often hold no campaign, and
        walking the campaigns to find them left those behind, active under an
        archived account.
        """
        advertising_account = self._create_advertising_account()
        empty_group = self.SocialAdvertisingCampaignGroup.create(
            {
                "name": "Empty group",
                "advertising_account_id": advertising_account.id,
            }
        )
        self.social_account_id.write({"active": False})
        self.assertFalse(empty_group.active)
        self.social_account_id.write({"active": True})
        self.assertTrue(empty_group.active)

    def test_archive_account_keeps_a_group_of_another_account(self):
        """The cascade only reaches the groups of the archived account."""
        other_account = self.SocialAccount.create(
            {"name": "Other account", "media_id": self.social_media_id.id}
        )
        other_advertising_account = self._create_advertising_account(
            account=other_account, remote_ref="urn:ad:other"
        )
        other_group = self.SocialAdvertisingCampaignGroup.create(
            {
                "name": "Group of another account",
                "advertising_account_id": other_advertising_account.id,
            }
        )
        self.social_account_id.write({"active": False})
        self.assertTrue(other_group.active)

    def test_remove_social_media_archives_campaigns(self):
        field = self.social_media_id._fields["media_type"]
        with patch.object(field, "selection", new=[("other_social", "Other social")]):
            self.social_media_id.write({"media_type": "other_social"})
            self.SocialAccount._remove_social_media("other_social")
        self.assertFalse(self.campaign_id.active)
        self.assertFalse(self.campaign_group_id.active)

    def test_autoselect_the_only_advertising_account(self):
        advertising_account = self._create_advertising_account(remote_ref="urn:ad:1")
        self.assertEqual(
            self.social_account_id._autoselect_advertising_account(),
            advertising_account,
        )
        self.assertTrue(advertising_account.is_current)

    def test_autoselect_ignores_another_environment(self):
        self._create_advertising_account(
            remote_ref="urn:ad:1", environment="production"
        )
        self.assertFalse(self.social_account_id._autoselect_advertising_account())

    def test_autoselect_with_several_candidates(self):
        """Nothing is chosen for the user when the environment leaves a doubt."""
        self._create_advertising_account(remote_ref="urn:ad:1")
        self._create_advertising_account(remote_ref="urn:ad:2")
        self.assertFalse(self.social_account_id._autoselect_advertising_account())
        self.assertFalse(
            self.social_account_id.advertising_account_ids.filtered("is_current")
        )

    def test_autoselect_keeps_the_choice_of_the_user(self):
        chosen = self._create_advertising_account(remote_ref="urn:ad:1")
        chosen.action_set_current()
        self.assertFalse(self.social_account_id._autoselect_advertising_account())
        self.assertTrue(chosen.is_current)

    def test_environment_change_autoselects_the_only_candidate(self):
        test_account = self._create_advertising_account(remote_ref="urn:ad:1")
        production_account = self._create_advertising_account(
            remote_ref="urn:ad:2", environment="production"
        )
        test_account.action_set_current()
        self.social_account_id.write({"environment": "production"})
        self.assertFalse(test_account.is_current)
        self.assertTrue(
            production_account.is_current,
            "The only advertising account of the new environment is chosen "
            "without asking the user again.",
        )

    def test_sync_advertising_accounts_autoselects_the_only_one(self):
        values = [
            {
                "name": "Advertising account",
                "remote_ref": "urn:ad:1",
                "environment": self.social_account_id.environment,
            }
        ]
        with patch(
            PATCH_ADVERTISING_ACCOUNT.format("_fetch_advertising_accounts"),
            autospec=True,
            return_value=values,
        ):
            advertising_accounts = self.social_account_id._sync_advertising_accounts()
        self.assertTrue(advertising_accounts.is_current)
        self.assertEqual(self.social_account_id.advertising_account_urn, "urn:ad:1")

    def test_campaign_counts_without_advertising_accounts(self):
        """The campaigns are only counted through the advertising accounts."""
        self.assertEqual(self.social_account_id.campaign_count, 0)
        self.assertEqual(self.social_account_id.campaign_group_count, 0)

    def test_campaign_counts_of_the_advertising_accounts(self):
        advertising_account = self._create_advertising_account(remote_ref="urn:ad:1")
        self.campaign_id.write({"advertising_account_id": advertising_account.id})
        self.campaign_group_id.write({"advertising_account_id": advertising_account.id})
        self.social_account_id.invalidate_recordset()
        self.assertEqual(self.social_account_id.campaign_count, 1)
        self.assertEqual(self.social_account_id.campaign_group_count, 1)

    def test_campaign_counts_ignore_another_account(self):
        other_account = self.SocialAccount.create(
            {"name": "Other account", "media_id": self.social_media_id.id}
        )
        advertising_account = self._create_advertising_account(
            account=other_account, remote_ref="urn:ad:2"
        )
        self.campaign_id.write({"advertising_account_id": advertising_account.id})
        self.social_account_id.invalidate_recordset()
        self.assertEqual(self.social_account_id.campaign_count, 0)
        self.assertEqual(other_account.campaign_count, 1)

    def test_action_open_campaigns(self):
        advertising_account = self._create_advertising_account(remote_ref="urn:ad:1")
        self.campaign_id.write({"advertising_account_id": advertising_account.id})
        action = self.social_account_id.action_open_campaigns()
        self.assertEqual(action["res_model"], "social.advertising.campaign")
        self.assertEqual(
            action["domain"],
            [("advertising_account_id", "in", advertising_account.ids)],
        )
        self.assertEqual(
            self.SocialAdvertisingCampaign.search(action["domain"]), self.campaign_id
        )

    def test_action_open_campaign_groups(self):
        advertising_account = self._create_advertising_account(remote_ref="urn:ad:1")
        advertising_account.action_set_current()
        self.campaign_group_id.write({"advertising_account_id": advertising_account.id})
        action = self.social_account_id.action_open_campaign_groups()
        self.assertEqual(action["res_model"], "social.advertising.campaign.group")
        self.assertEqual(
            action["context"]["default_advertising_account_id"],
            advertising_account.id,
            msg="A group created from here belongs to the advertising account "
            "in use.",
        )
        self.assertEqual(
            self.SocialAdvertisingCampaignGroup.search(action["domain"]),
            self.campaign_group_id,
        )

    def test_action_open_campaign_groups_without_a_current_account(self):
        self._create_advertising_account(remote_ref="urn:ad:1")
        action = self.social_account_id.action_open_campaign_groups()
        self.assertNotIn("default_advertising_account_id", action["context"])

    def test_purge_account_keeps_the_campaigns(self):
        """What was written here and never published is work, not a mirror."""
        self.social_account_id.action_archive_account()
        self.social_account_id.action_purge_account()
        self.campaign_id.invalidate_recordset()
        self.assertTrue(self.campaign_id.exists())
        self.assertFalse(self.campaign_id.account_ids)
        self.assertTrue(self.campaign_group_id.exists())

    def _create_remote_campaign(self, **values):
        """Return a campaign of the account as the social media answers it."""
        advertising_account = self._create_advertising_account(remote_ref="urn:ad:5")
        group = self.SocialAdvertisingCampaignGroup.create(
            {
                "name": "Remote group",
                "remote_ref": "urn:group:5",
                "advertising_account_id": advertising_account.id,
            }
        )
        campaign = self.SocialAdvertisingCampaign.create(
            dict(
                {
                    "name": "Remote campaign",
                    "remote_ref": "urn:campaign:5",
                    "campaign_group_id": group.id,
                    "advertising_account_id": advertising_account.id,
                },
                **values,
            )
        )
        return campaign, group

    def test_purge_account_deletes_the_campaigns_of_the_social_media(self):
        """A campaign of the social media cannot be reached without its account."""
        campaign, group = self._create_remote_campaign()
        self.social_account_id.action_purge_account()
        self.assertFalse(campaign.exists())
        self.assertFalse(group.exists())

    def test_purge_account_keeps_a_campaign_of_another_account(self):
        """A campaign shared with an account that stays is not a leftover."""
        other_account = self.SocialAccount.create(
            {"name": "Other account", "media_id": self.social_media_id.id}
        )
        campaign, group = self._create_remote_campaign(
            account_ids=[Command.set([self.social_account_id.id, other_account.id])]
        )
        self.social_account_id.action_purge_account()
        self.assertTrue(campaign.exists())
        self.assertEqual(campaign.account_ids, other_account)
        self.assertTrue(group.exists())

    def test_purge_account_keeps_a_group_still_holding_a_campaign(self):
        """A group is only dropped once nothing hangs from it."""
        campaign, group = self._create_remote_campaign()
        local_campaign = self.SocialAdvertisingCampaign.create(
            {"name": "Written here", "campaign_group_id": group.id}
        )
        self.social_account_id.action_purge_account()
        self.assertFalse(campaign.exists())
        self.assertTrue(group.exists())
        self.assertEqual(group.campaign_ids, local_campaign)
