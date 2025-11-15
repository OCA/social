# Copyright 2025 Binhex <https://www.binhex.cloud>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import json
from unittest.mock import patch

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

    def test_delete_account(self):
        self.social_account_id.delete_account()
        self.assertFalse(self.social_post_id.active)
        self.assertFalse(self.social_post_account_id.active)
        self.assertFalse(self.social_account_id.active)

    def test_compute_account_url(self):
        fake_fields = [
            (
                "fake_other_social_account_urn",
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
            ("fake_account_urn", "https://www.failed.com/company/2333/admin")
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

    def test_need_update(self):
        Bus = self.env["bus.bus"]
        with patch.object(type(Bus), "_sendone", autospec=True) as patch_sendone:
            self.social_account_id._need_update()
            patch_sendone.assert_called_once()
            