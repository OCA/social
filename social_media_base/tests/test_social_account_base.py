# Copyright 2025 Binhex <https://www.binhex.cloud>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import json
from unittest.mock import patch

from odoo.exceptions import AccessError

from odoo.addons.social_media_base.tests.test_social_common import (
    TestSocialMediaBaseCommon,
)

from .test_social_common import PATCH_ACCOUNT


class TestSocialAccountBase(TestSocialMediaBaseCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.User = cls.env["res.users"]
        cls.any_user = cls.User.create(
            {
                "name": "User 1",
                "login": "user_1_test",
                "email": "user1@test.example.com",
                "password": "test1234",
                "groups_id": [(6, 0, [cls.env.ref("base.group_user").id])],
            }
        )

    def test_compute_is_property_account(self):
        account_id = self.SocialAccount.create(
            {"name": "Account 1", "media_id": self.social_media_id.id}
        )
        account_not_property = account_id.with_user(self.any_user)
        self.assertNotEqual(account_not_property.env.user, self.env.user)
        self.assertFalse(account_not_property.is_property_account)

        account_id = self.SocialAccount.create(
            {"name": "Account 2", "media_id": self.social_media_id.id}
        )
        account_property = account_id.with_user(self.env.ref("base.user_root"))
        self.assertEqual(account_property.env.user, self.env.user)
        self.assertTrue(account_property.is_property_account)

    def test_compute_display_name(self):
        self.social_account_id._compute_display_name()
        self.assertEqual(self.social_account_id.display_name, "Linkedin")

    @patch(PATCH_ACCOUNT.format("_get_chart_account_statistics"))
    def test_get_chart_account_statistics(self, mock_get_chart_account_statistics):
        self.social_account_id.get_chart_account_statistics()
        mock_get_chart_account_statistics.assert_called_once()

    def test_archive_account(self):
        self.social_account_id.action_archive_account()
        self.assertFalse(self.social_post_id.active)
        self.assertFalse(self.social_post_account_id.active)
        self.assertFalse(self.social_account_id.active)

    def _create_social_media_user(self):
        return self.User.create(
            {
                "name": "Social user",
                "login": "social_user_test",
                "groups_id": [
                    (
                        6,
                        0,
                        [
                            self.env.ref("base.group_user").id,
                            self.env.ref(
                                "social_media_base.group_social_media_user"
                            ).id,
                        ],
                    )
                ],
            }
        )

    def _create_social_media_manager(self):
        return self.User.create(
            {
                "name": "Social manager",
                "login": "social_manager_test",
                "groups_id": [
                    (
                        6,
                        0,
                        [
                            self.env.ref("base.group_user").id,
                            self.env.ref(
                                "social_media_base.group_social_media_manager"
                            ).id,
                        ],
                    )
                ],
            }
        )

    def test_find_account_to_associate(self):
        media_type = self.social_account_id.media_type
        self.social_account_id.write(
            {"remote_ref": "urn:li:organization:1", "username": "the_account"}
        )
        found = self.SocialAccount._find_account_to_associate(
            media_type, "urn:li:organization:1"
        )
        self.assertEqual(found, self.social_account_id)
        self.assertFalse(
            self.SocialAccount._find_account_to_associate(
                media_type, "urn:li:organization:2"
            ),
            "An account of another organization must never be reused",
        )
        self.assertFalse(
            self.SocialAccount._find_account_to_associate(
                media_type, "urn:li:organization:2", username="the_account"
            ),
            "The user name is not a fallback for accounts that do have a "
            "remote reference",
        )

    def test_find_account_to_associate_without_remote_ref(self):
        media_type = self.social_account_id.media_type
        self.social_account_id.write({"remote_ref": False, "username": "legacy"})
        found = self.SocialAccount._find_account_to_associate(
            media_type, "urn:li:organization:1", username="legacy"
        )
        self.assertEqual(
            found,
            self.social_account_id,
            "Accounts stored before the remote reference existed are still "
            "relinked by their user name",
        )

    def test_check_can_associate(self):
        social_user = self._create_social_media_user()
        self.social_account_id.write({"user_id": self.env.user.id})
        self.social_account_id._check_can_associate()
        with self.assertRaises(AccessError):
            self.social_account_id.with_user(social_user)._check_can_associate()
        manager = self._create_social_media_manager()
        self.social_account_id.with_user(manager)._check_can_associate()

    def test_can_manage_account(self):
        social_user = self._create_social_media_user()
        manager = self._create_social_media_manager()
        self.social_account_id.write({"user_id": self.env.user.id})
        self.assertTrue(self.social_account_id.can_manage_account)
        self.assertFalse(
            self.social_account_id.with_user(social_user).can_manage_account,
            "A user who is not the responsible one cannot manage the account",
        )
        self.assertTrue(
            self.social_account_id.with_user(manager).can_manage_account,
            "A social media administrator can manage any account",
        )

    def test_wizard_cannot_touch_account_of_another_user(self):
        social_user = self._create_social_media_user()
        self.social_account_id.write({"user_id": self.env.user.id})
        wizard = self.WizardAccount.with_user(social_user).create(
            {
                "media_id": self.social_media_id.id,
                "account_id": self.social_account_id.id,
                "update_keys": True,
            }
        )
        with self.assertRaises(AccessError):
            wizard.update_account()
        with self.assertRaises(AccessError):
            wizard.action_associate_social_account()

    def test_wizard_allows_the_responsible_user(self):
        social_user = self._create_social_media_user()
        self.social_account_id.write({"user_id": social_user.id})
        wizard = self.WizardAccount.with_user(social_user).create(
            {
                "media_id": self.social_media_id.id,
                "account_id": self.social_account_id.id,
            }
        )
        wizard._check_account_access()

    def test_purge_account(self):
        group = self.UtmGroupCampaign.create({"name": "Purge Group"})
        campaign = self.UtmCampaign.create(
            {
                "name": "Purge Campaign",
                "campaign_group_id": group.id,
                "account_id": self.social_account_id.id,
            }
        )
        post = self.social_post_id
        post_account = self.social_post_account_id
        self.social_account_id.action_archive_account()
        action = self.social_account_id.action_purge_account()
        self.assertEqual(action.get("res_model"), "social.account")
        self.assertEqual(action.get("target"), "main")
        self.assertFalse(self.social_account_id.exists())
        self.assertFalse(post_account.exists())
        self.assertFalse(post.exists())
        campaign.invalidate_recordset()
        self.assertTrue(campaign.exists())
        self.assertFalse(campaign.account_id)
        self.assertTrue(group.exists())

    def test_purge_account_keeps_shared_post(self):
        other_account = self.SocialAccount.create(
            {"name": "Other account", "media_id": self.social_media_id.id}
        )
        shared_post = self.SocialPost.create(
            {
                "message": "Shared message",
                "account_ids": [(6, 0, [self.social_account_id.id, other_account.id])],
            }
        )
        self.social_account_id.action_archive_account()
        self.social_account_id.action_purge_account()
        self.assertTrue(shared_post.exists())
        self.assertEqual(shared_post.account_ids, other_account)

    def test_purge_account_requires_manager(self):
        social_user = self._create_social_media_user()
        with self.assertRaises(AccessError):
            self.social_account_id.with_user(social_user).action_purge_account()

    def test_user_cannot_unlink_account(self):
        social_user = self._create_social_media_user()
        account = self.SocialAccount.with_user(social_user).create(
            {"name": "Own account", "media_id": self.social_media_id.id}
        )
        with self.assertRaises(AccessError):
            account.unlink()

    def test_remove_social_media(self):
        field = self.social_media_id._fields["media_type"]
        with patch.object(field, "selection", new=[("other_social", "Other social")]):
            self.social_media_id.write({"media_type": "other_social"})
            self.social_account_id.write(
                {
                    "remote_ref": "remote-account-1",
                    "access_token": "token",
                    "refresh_access_token": "refresh-token",
                }
            )
            group = self.UtmGroupCampaign.create({"name": "Removal Group"})
            self.UtmCampaign.create(
                {
                    "name": "Removal Campaign",
                    "campaign_group_id": group.id,
                    "account_id": self.social_account_id.id,
                }
            )
            self.SocialAccount._remove_social_media("other_social")
        self.assertFalse(group.active)
        account_sudo = self.social_account_id.sudo()
        self.assertFalse(account_sudo.access_token)
        self.assertFalse(account_sudo.refresh_access_token)
        self.assertFalse(self.social_account_id.active)
        self.assertFalse(self.social_post_account_id.active)
        self.assertEqual(self.social_account_id.remote_ref, "remote-account-1")

    def test_remove_social_media_other_media_untouched(self):
        field = self.social_media_id._fields["media_type"]
        with patch.object(field, "selection", new=[("other_social", "Other social")]):
            self.social_media_id.write({"media_type": "other_social"})
            self.social_account_id.write({"access_token": "token"})
            self.SocialAccount._remove_social_media("not_this_media")
        self.assertTrue(self.social_account_id.active)
        self.assertEqual(self.social_account_id.sudo().access_token, "token")

    def test_archive_account_cascade(self):
        group = self.UtmGroupCampaign.create({"name": "Cascade Group"})
        campaign = self.UtmCampaign.create(
            {
                "name": "Cascade Campaign",
                "campaign_group_id": group.id,
                "account_id": self.social_account_id.id,
            }
        )
        self.social_account_id.write({"active": False})
        self.assertFalse(self.social_account_id.active)
        self.assertFalse(self.social_post_id.active)
        self.assertFalse(self.social_post_account_id.active)
        self.assertFalse(campaign.active)
        self.assertFalse(group.active)
        self.social_account_id.write({"active": True})
        self.assertTrue(self.social_account_id.active)
        self.assertTrue(self.social_post_id.active)
        self.assertTrue(self.social_post_account_id.active)
        self.assertTrue(campaign.active)
        self.assertTrue(group.active)

    def test_compute_account_url(self):
        fake_fields = [
            (
                "other_social",
                "https://www.failed.com/company/id1234account/admin",
            )
        ]
        field = self.social_media_id._fields["media_type"]
        with patch.object(
            type(self.social_account_id),
            "_fields_account_url",
            autospec=True,
            return_value=fake_fields,
        ), patch.object(
            field,
            "selection",
            new=[("other_social", "Other social")],
        ):
            self.social_media_id.write({"media_type": "other_social"})
            self.assertEqual(
                self.social_account_id.account_url,
                "https://www.failed.com/company/id1234account/admin",
            )

    def test_compute_account_url_failed(self):
        fake_failed_fields = [
            ("other_social", "https://www.failed.com/company/2333/admin")
        ]
        with patch.object(
            type(self.social_account_id),
            "_fields_account_url",
            autospec=True,
            return_value=fake_failed_fields,
        ):
            self.assertFalse(self.social_account_id.account_url)

    def test_compute_account_url_failed_continue(self):
        fake_failed_continue = ["Y"]
        with patch.object(
            type(self.social_account_id),
            "_fields_account_url",
            autospec=True,
            return_value=fake_failed_continue,
        ):
            self.assertFalse(self.social_account_id.account_url)

    def test_filter_statistics(self):
        fake_statistics = {"stats_fake": (5, 10, 15, 20, 25, 30)}
        statistics = self.social_account_id._filter_statistics(fake_statistics)
        self.assertEqual(statistics["click_count"], fake_statistics["stats_fake"][0])
        self.assertEqual(statistics["like_count"], fake_statistics["stats_fake"][1])
        self.assertEqual(statistics["comment_count"], fake_statistics["stats_fake"][2])
        self.assertEqual(statistics["share_count"], fake_statistics["stats_fake"][3])
        self.assertEqual(statistics["engagement"], fake_statistics["stats_fake"][4])
        self.assertEqual(
            statistics["impression_count"], fake_statistics["stats_fake"][5]
        )

    def test_update_posts_statistics(self):
        fake_statistics = [{"like_count": 5}]
        with patch.object(
            type(self.social_account_id),
            "_update_posts_statistics",
            autospec=True,
            return_value=fake_statistics,
        ):
            update_statistics = self.social_account_id.update_posts_statistics()
            load_update_statistics = json.loads(update_statistics)
            self.assertEqual(load_update_statistics[0]["like_count"], 5)

    def test_trigger_initial_sync(self):
        CronTrigger = self.env["ir.cron.trigger"]
        cron = self.env.ref("social_media_base.initial_sync_account_job")
        before = CronTrigger.search_count([("cron_id", "=", cron.id)])
        self.social_account_id._trigger_initial_sync()
        after = CronTrigger.search_count([("cron_id", "=", cron.id)])
        self.assertEqual(after, before + 1)

    def test_load_ads_accounts(self):
        fake_statistics = {"campaign": "Campaign test"}
        with patch.object(
            type(self.social_account_id),
            "_load_ads_accounts",
            autospec=True,
            return_value=fake_statistics,
        ):
            ads = self.social_account_id.load_ads_accounts()
            self.assertEqual(ads["campaign"], fake_statistics["campaign"])

    def test_load_ads_accounts_default_payload(self):
        """The payload must always expose ``ads`` as a list, even with no data."""
        ads = self.social_account_id.load_ads_accounts()
        self.assertIsInstance(ads["ads"], list)

    def test_need_update(self):
        Bus = self.env["bus.bus"]
        with patch.object(type(Bus), "_sendone", autospec=True) as patch_sendone:
            self.social_account_id._need_update()
            patch_sendone.assert_called_once()

    def test_get_social_dashboard_url(self):
        url = self.SocialAccount._get_social_dashboard_url()
        menu = self.env.ref("social_media_base.social_network_stream_post_menu")
        self.assertEqual(url, f"/web#menu_id={menu.id}&action={menu.action.id}")
