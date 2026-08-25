# Copyright 2026 Binhex <https://www.binhex.cloud>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from unittest.mock import patch

import psycopg2

from odoo import fields
from odoo.exceptions import AccessError, UserError
from odoo.tests import tagged
from odoo.tools import mute_logger

from .test_social_advertising_common import (
    PATCH_ADVERTISING_ACCOUNT,
    TestSocialAdvertisingCommon,
)


class TestSocialAdvertisingAdCommon(TestSocialAdvertisingCommon):
    """Fixture of the ads: an advertising account in use and its values."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.SocialAdvertisingAd = cls.env["social.advertising.ad"]
        cls.advertising_account_id = cls._create_advertising_account(
            remote_ref="urn:ad:1"
        )
        cls.advertising_account_id.action_set_current()

    def _ad_values(self, remote_ref="urn:ad:creative:1", **values):
        return dict(
            {
                "remote_ref": remote_ref,
                "advertising_account_id": self.advertising_account_id.id,
                "campaign_id": self.campaign_id.id,
                "impression_count": 100,
                "click_count": 10,
                "statistics_date_from": "2026-01-01",
                "statistics_date_to": "2026-01-31",
            },
            **values,
        )

    def _patch_fetch_ads(self, values):
        return patch(
            PATCH_ADVERTISING_ACCOUNT.format("_fetch_ads"),
            autospec=True,
            return_value=values,
        )

    def _patch_connector(self):
        """Make the test media look like one a connector module supports."""
        return patch(
            PATCH_ADVERTISING_ACCOUNT.format("_advertising_media_types"),
            autospec=True,
            return_value=[self.social_account_id.media_type],
        )


class TestSocialAdvertisingAd(TestSocialAdvertisingAdCommon):
    def test_kanban_declares_the_media_of_the_ad(self):
        """The card draws the icon of the media, which is a record field.

        Without the field the template reads ``undefined`` and the card
        breaks on the client, so the declaration is part of the fix.
        """
        arch = self.env.ref(
            "social_media_advertising.social_advertising_ad_view_kanban"
        ).arch
        self.assertIn('name="media_id"', arch)
        self.assertIn("/web/image/social.media/", arch)
        self.assertNotIn("static/img", arch)

    def test_fetch_ads_default(self):
        self.assertEqual(self.social_account_id._fetch_ads(), [])

    def test_fetch_ad_refs_default(self):
        self.assertEqual(self.social_account_id._fetch_ad_refs(), set())

    def test_sync_ads_creates_the_ads(self):
        with self._patch_fetch_ads([self._ad_values()]):
            ads = self.social_account_id._sync_ads()
        self.assertEqual(len(ads), 1)
        self.assertEqual(ads.remote_ref, "urn:ad:creative:1")
        self.assertEqual(ads.account_id, self.social_account_id)
        self.assertTrue(ads.last_sync_date)
        self.assertEqual(
            ads.advertising_account_id,
            self.advertising_account_id,
            msg="The ad keeps the advertising account it was served from.",
        )
        self.assertTrue(ads.advertising_account_is_current)

    def test_sync_ads_is_idempotent(self):
        """Two runs update the same ad instead of creating it again."""
        with self._patch_fetch_ads([self._ad_values()]):
            self.social_account_id._sync_ads()
            ads = self.social_account_id._sync_ads()
        self.assertEqual(len(ads), 1)
        self.assertEqual(
            self.SocialAdvertisingAd.search_count(
                [("remote_ref", "=", "urn:ad:creative:1")]
            ),
            1,
        )

    def test_sync_ads_updates_the_statistics(self):
        with self._patch_fetch_ads([self._ad_values()]):
            self.social_account_id._sync_ads()
        with self._patch_fetch_ads([self._ad_values(click_count=25)]):
            ads = self.social_account_id._sync_ads()
        self.assertEqual(ads.click_count, 25)

    def test_sync_ads_archives_what_the_social_media_dropped(self):
        """An ad that is not served anymore keeps its statistics, archived."""
        with self._patch_fetch_ads(
            [self._ad_values(), self._ad_values("urn:ad:creative:2")]
        ):
            self.social_account_id._sync_ads()
        with self._patch_fetch_ads([self._ad_values()]):
            self.social_account_id._sync_ads()
        dropped = self.SocialAdvertisingAd.with_context(active_test=False).search(
            [("remote_ref", "=", "urn:ad:creative:2")]
        )
        self.assertTrue(dropped, msg="The ad is archived, never deleted.")
        self.assertFalse(dropped.active)
        self.assertEqual(dropped.impression_count, 100)
        self.assertEqual(dropped.click_count, 10)
        self.assertEqual(
            (dropped.statistics_date_from, dropped.statistics_date_to),
            (fields.Date.to_date("2026-01-01"), fields.Date.to_date("2026-01-31")),
            msg="A figure without its window cannot be read.",
        )

    def test_sync_ads_brings_an_archived_ad_back(self):
        """An ad served again is the same record, unarchived."""
        with self._patch_fetch_ads([self._ad_values()]):
            self.social_account_id._sync_ads()
        with self._patch_fetch_ads([]):
            self.social_account_id._sync_ads()
        with self._patch_fetch_ads([self._ad_values()]):
            ads = self.social_account_id._sync_ads()
        self.assertEqual(len(ads), 1)
        self.assertTrue(ads.active)

    def test_sync_ads_keeps_everything_on_an_empty_answer(self):
        """An empty answer cannot be told apart from a transient failure."""
        with self._patch_fetch_ads([self._ad_values()]):
            self.social_account_id._sync_ads()
        with self._patch_fetch_ads([]):
            ads = self.social_account_id._sync_ads()
        self.assertEqual(len(ads), 1)
        self.assertTrue(ads.active)

    def test_sync_ads_keeps_the_ads_of_another_advertising_account(self):
        """Choosing another advertising account must not archive the old ads."""
        other_advertising_account = self._create_advertising_account(
            remote_ref="urn:ad:2"
        )
        with self._patch_fetch_ads([self._ad_values()]):
            self.social_account_id._sync_ads()
        with self._patch_fetch_ads(
            [
                self._ad_values(
                    "urn:ad:creative:2",
                    advertising_account_id=other_advertising_account.id,
                )
            ]
        ):
            self.social_account_id._sync_ads()
        first = self.SocialAdvertisingAd.with_context(active_test=False).search(
            [("remote_ref", "=", "urn:ad:creative:1")]
        )
        self.assertTrue(
            first.active,
            msg="The social media only answered for the other advertising account.",
        )

    def test_advertising_account_is_current_follows_the_chosen_one(self):
        other_advertising_account = self._create_advertising_account(
            remote_ref="urn:ad:2"
        )
        with self._patch_fetch_ads([self._ad_values()]):
            ads = self.social_account_id._sync_ads()
        other_advertising_account.action_set_current()
        self.assertFalse(
            ads.advertising_account_is_current,
            msg="The view tells the ads of the advertising account no longer in use.",
        )

    def test_action_sync_ads_without_a_connector(self):
        res = self.social_account_id.action_sync_ads()
        self.assertFalse(res["success"])
        self.assertEqual(res["ads"], 0)

    def test_action_sync_ads_success(self):
        with self._patch_connector(), self._patch_fetch_ads([self._ad_values()]):
            self.social_account_id.invalidate_recordset()
            res = self.social_account_id.action_sync_ads()
        self.assertTrue(res["success"])
        self.assertEqual(res["ads"], 1)

    def test_action_sync_ads_reports_the_error(self):
        with self._patch_connector(), patch(
            PATCH_ADVERTISING_ACCOUNT.format("_fetch_ads"),
            autospec=True,
            side_effect=UserError("Token revoked"),
        ):
            self.social_account_id.invalidate_recordset()
            res = self.social_account_id.action_sync_ads()
        self.assertFalse(res["success"])
        self.assertEqual(res["message"], "Token revoked")

    def test_action_sync_all_ads_notify(self):
        with self._patch_connector(), self._patch_fetch_ads([self._ad_values()]):
            self.social_account_id.invalidate_recordset()
            res = self.env["social.account"].action_sync_all_ads_notify()
        self.assertEqual(res["params"]["type"], "success")

    def test_action_sync_all_ads_notify_without_accounts(self):
        res = self.env["social.account"].action_sync_all_ads_notify()
        self.assertEqual(res["params"]["type"], "success")
        self.assertIn("No account", res["params"]["message"])

    @mute_logger("odoo.addons.social_media_advertising.models.social_account")
    def test_action_sync_all_ads_notify_survives_a_failing_account(self):
        """One account the social media refuses must not stop the others."""
        with self._patch_connector(), patch(
            PATCH_ADVERTISING_ACCOUNT.format("_fetch_ads"),
            autospec=True,
            side_effect=ValueError("boom"),
        ):
            self.social_account_id.invalidate_recordset()
            res = self.env["social.account"].action_sync_all_ads_notify()
        self.assertEqual(res["params"]["type"], "danger")
        self.assertIn(self.social_account_id.display_name, res["params"]["message"])

    def test_check_ads_updates_flags_the_new_ads(self):
        with patch(
            PATCH_ADVERTISING_ACCOUNT.format("_fetch_ad_refs"),
            autospec=True,
            return_value={"urn:ad:creative:1"},
        ):
            found = self.social_account_id._check_ads_updates()
        self.assertTrue(found)
        self.assertTrue(self.social_account_id.ads_need_update)

    def test_check_ads_updates_without_news(self):
        with self._patch_fetch_ads([self._ad_values()]):
            self.social_account_id._sync_ads()
        with patch(
            PATCH_ADVERTISING_ACCOUNT.format("_fetch_ad_refs"),
            autospec=True,
            return_value={"urn:ad:creative:1"},
        ):
            found = self.social_account_id._check_ads_updates()
        self.assertFalse(found)
        self.assertFalse(self.social_account_id.ads_need_update)

    def test_check_ads_updates_without_an_answer(self):
        found = self.social_account_id._check_ads_updates()
        self.assertFalse(found)
        self.assertFalse(self.social_account_id.ads_need_update)

    def test_get_ads_need_update(self):
        """The kanban reads the stored flag back, the bus is not its only source."""
        Account = self.env["social.account"]
        self.assertFalse(Account.get_ads_need_update())
        self.social_account_id.write({"ads_need_update": True})
        self.assertTrue(Account.get_ads_need_update())

    def test_notify_ads_need_update_reaches_the_responsible(self):
        """The frontend subscribes to this exact type and payload."""
        Bus = self.env["bus.bus"]
        with patch.object(type(Bus), "_sendone", autospec=True) as patch_sendone:
            self.social_account_id._notify_ads_need_update()
        patch_sendone.assert_called_once()
        self.assertEqual(
            patch_sendone.call_args[0][1], self.social_account_id.user_id.partner_id
        )
        self.assertEqual(patch_sendone.call_args[0][2], "social_ads_need_update")
        self.assertEqual(patch_sendone.call_args[0][3], {"need_update": True})

    def test_notify_ads_need_update_falls_back_to_the_current_user(self):
        """Without an account to address, the message goes to whoever asked."""
        Bus = self.env["bus.bus"]
        with patch.object(type(Bus), "_sendone", autospec=True) as patch_sendone:
            self.env["social.account"]._notify_ads_need_update(need_update=False)
        self.assertEqual(patch_sendone.call_args[0][1], self.env.user.partner_id)
        self.assertEqual(patch_sendone.call_args[0][3], {"need_update": False})

    def test_sync_ads_clears_the_flag(self):
        self.social_account_id.write({"ads_need_update": True})
        with self._patch_fetch_ads([self._ad_values()]):
            self.social_account_id._sync_ads()
        self.assertFalse(self.social_account_id.ads_need_update)

    def test_run_check_ads_updates_skips_the_accounts_without_advertising(self):
        """An account of a media no connector serves is never even read."""
        with patch(
            PATCH_ADVERTISING_ACCOUNT.format("_fetch_ad_refs"),
            autospec=True,
            return_value={"urn:ad:creative:1"},
        ) as mock_fetch:
            self.env["social.account"]._run_check_ads_updates()
        mock_fetch.assert_not_called()
        self.assertFalse(self.social_account_id.ads_need_update)

    def test_run_check_ads_updates_flags_the_accounts(self):
        with self._patch_connector(), patch(
            PATCH_ADVERTISING_ACCOUNT.format("_fetch_ad_refs"),
            autospec=True,
            return_value={"urn:ad:creative:1"},
        ):
            self.env["social.account"]._run_check_ads_updates()
        self.assertTrue(self.social_account_id.ads_need_update)

    @mute_logger("odoo.addons.social_media_advertising.models.social_account")
    def test_run_check_ads_updates_survives_a_failing_account(self):
        with self._patch_connector(), patch(
            PATCH_ADVERTISING_ACCOUNT.format("_fetch_ad_refs"),
            autospec=True,
            side_effect=ValueError("boom"),
        ):
            self.env["social.account"]._run_check_ads_updates()
        self.assertFalse(self.social_account_id.ads_need_update)

    def test_archive_account_archives_its_ads(self):
        with self._patch_fetch_ads([self._ad_values()]):
            ads = self.social_account_id._sync_ads()
        self.social_account_id.write({"active": False})
        self.assertFalse(ads.active)

    def test_unarchive_account_leaves_the_ads_archived(self):
        """Unarchiving must not resurrect the ads the social media dropped."""
        with self._patch_fetch_ads([self._ad_values()]):
            ads = self.social_account_id._sync_ads()
        self.social_account_id.write({"active": False})
        self.social_account_id.write({"active": True})
        self.assertFalse(ads.active)
        with self._patch_fetch_ads([self._ad_values()]):
            self.social_account_id._sync_ads()
        self.assertTrue(ads.active, msg="The next sync brings back what is served.")

    def test_delete_account_deletes_its_ads(self):
        """The ads of an account are gone with it, they mirror nothing else."""
        account = self.SocialAccount.create(
            {"name": "Account to delete", "media_id": self.social_media_id.id}
        )
        with self._patch_fetch_ads([self._ad_values(advertising_account_id=False)]):
            ads = account._sync_ads()
        self.assertTrue(ads)
        account.unlink()
        self.assertFalse(ads.exists())

    @mute_logger("odoo.sql_db")
    def test_remote_ref_is_unique_per_account(self):
        self.SocialAdvertisingAd.create(
            dict(self._ad_values(), account_id=self.social_account_id.id)
        )
        with self.assertRaises(psycopg2.IntegrityError):
            with self.env.cr.savepoint():
                self.SocialAdvertisingAd.create(
                    dict(self._ad_values(), account_id=self.social_account_id.id)
                )

    def test_delete_remote_ad_is_not_available_without_a_connector(self):
        """Nothing is deletable until a connector says how."""
        ad = self.SocialAdvertisingAd.create(
            dict(self._ad_values(), account_id=self.social_account_id.id)
        )
        self.assertFalse(ad.can_delete_remote_ad)
        with self.assertRaises(UserError):
            ad.action_delete_remote_ad()

    def test_purge_an_archived_ad(self):
        """The way out for an ad the social media stopped serving."""
        ad = self.SocialAdvertisingAd.create(
            dict(self._ad_values(), account_id=self.social_account_id.id)
        )
        ad._register_remote_ad_gone()
        self.assertFalse(ad.active)
        self.assertEqual(ad.impression_count, 100)
        self.assertEqual(
            (ad.statistics_date_from, ad.statistics_date_to),
            (fields.Date.to_date("2026-01-01"), fields.Date.to_date("2026-01-31")),
            msg="Archiving keeps the figures and the window they cover.",
        )
        action = ad.action_purge_ad()
        self.assertFalse(ad.exists())
        self.assertEqual(action["res_model"], "social.advertising.ad")

    def test_purge_is_refused_on_a_served_ad(self):
        """Deleting an ad still answered only loses its statistics."""
        ad = self.SocialAdvertisingAd.create(
            dict(self._ad_values(), account_id=self.social_account_id.id)
        )
        with self.assertRaises(UserError):
            ad.action_purge_ad()
        self.assertTrue(ad.exists())

    def test_name_says_the_post_is_not_available(self):
        """The remote reference names nothing to the user."""
        ad = self.SocialAdvertisingAd.create(
            dict(self._ad_values(), account_id=self.social_account_id.id)
        )
        self.assertEqual(ad.name, "Post not available")
        self.assertNotIn("urn:ad:creative:1", ad.name)

    def test_name_is_the_message_of_the_promoted_publication(self):
        ad = self.SocialAdvertisingAd.create(
            dict(
                self._ad_values(),
                account_id=self.social_account_id.id,
                post_account_id=self.social_post_account_id.id,
            )
        )
        self.assertEqual(ad.name, self.social_post_account_id.message)

    def test_ad_count_and_action(self):
        with self._patch_fetch_ads(
            [self._ad_values(), self._ad_values("urn:ad:creative:2")]
        ):
            self.social_account_id._sync_ads()
        self.social_account_id.invalidate_recordset()
        self.assertEqual(self.social_account_id.ad_count, 2)
        action = self.social_account_id.action_open_ads()
        self.assertEqual(action["res_model"], "social.advertising.ad")
        self.assertEqual(
            self.SocialAdvertisingAd.search_count(action["domain"]),
            self.social_account_id.ad_count,
        )

    def test_generic_ad_action_has_no_domain(self):
        """The generic list of ads is the unfiltered one.

        It is the fallback of ``_advertising_ad_action`` and the action
        ``action_open_ads`` narrows, so a domain of its own would silently
        cut both.
        """
        action = self.env.ref("social_media_advertising.social_advertising_ad_action")
        self.assertFalse(action.domain)
        self.assertEqual(
            self.SocialAdvertisingAd._advertising_ad_action()["xml_id"],
            "social_media_advertising.social_advertising_ad_action",
        )

    def test_action_open_url(self):
        ad = self.SocialAdvertisingAd.create(
            dict(
                self._ad_values(),
                account_id=self.social_account_id.id,
                url="https://example.test/ad",
            )
        )
        action = ad.action_open_url()
        self.assertEqual(action["type"], "ir.actions.act_url")
        self.assertEqual(action["url"], "https://example.test/ad")

    def test_action_open_url_without_url(self):
        ad = self.SocialAdvertisingAd.create(
            dict(self._ad_values(), account_id=self.social_account_id.id)
        )
        self.assertFalse(ad.action_open_url())

    def test_action_open_post_account(self):
        ad = self.SocialAdvertisingAd.create(
            dict(
                self._ad_values(),
                account_id=self.social_account_id.id,
                post_account_id=self.social_post_account_id.id,
            )
        )
        action = ad.action_open_post_account()
        self.assertEqual(action["res_model"], "social.post.account")
        self.assertEqual(action["res_id"], self.social_post_account_id.id)

    def test_campaign_of_the_ad_survives_the_campaign_removal(self):
        """Dropping a campaign must not take its ads with it."""
        ad = self.SocialAdvertisingAd.create(
            dict(self._ad_values(), account_id=self.social_account_id.id)
        )
        self.campaign_id.unlink()
        self.assertTrue(ad.exists())
        self.assertFalse(ad.campaign_id)

    def test_ads_of_several_accounts_do_not_mix(self):
        other_account = self.SocialAccount.create(
            {
                "name": "Other account",
                "media_id": self.social_media_id.id,
                "user_id": self.env.user.id,
            }
        )
        other_advertising_account = self._create_advertising_account(
            account=other_account, remote_ref="urn:ad:9"
        )
        with self._patch_fetch_ads([self._ad_values()]):
            self.social_account_id._sync_ads()
        with self._patch_fetch_ads(
            [
                self._ad_values(
                    advertising_account_id=other_advertising_account.id,
                )
            ]
        ):
            other_ads = other_account._sync_ads()
        self.assertEqual(len(other_ads), 1)
        self.assertEqual(
            self.SocialAdvertisingAd.search_count(
                [("remote_ref", "=", "urn:ad:creative:1")]
            ),
            2,
            msg="The same creative reference may exist on two accounts.",
        )


@tagged("post_install", "-at_install")
class TestSocialAdvertisingAdSecurity(TestSocialAdvertisingAdCommon):
    """Access rights and record rules of the ads.

    Users are created here, so every module has to be in the registry.
    """

    def test_delete_remote_ad_is_refused_to_another_user(self):
        """Only the responsible user and the administrators may delete."""
        ad = self.SocialAdvertisingAd.create(
            dict(self._ad_values(), account_id=self.social_account_id.id)
        )
        self.social_account_id.user_id = self._create_social_media_user(
            login="ad_delete_owner"
        )
        other_user = self._create_social_media_user(login="ad_delete_other")
        with self.assertRaises(AccessError):
            ad.with_user(other_user).action_delete_remote_ad()

    def test_delete_remote_ad_is_allowed_to_the_manager(self):
        """An administrator acts on the ads of any account."""
        ad = self.SocialAdvertisingAd.create(
            dict(self._ad_values(), account_id=self.social_account_id.id)
        )
        self.social_account_id.user_id = self._create_social_media_user(
            login="ad_delete_owner_manager"
        )
        manager = self._create_social_media_manager(login="ad_delete_manager")
        # The hook of the base module is the one refusing here, not the
        # permission check, which is what tells the two apart.
        with self.assertRaises(UserError):
            ad.with_user(manager).action_delete_remote_ad()

    def test_a_user_only_sees_the_ads_of_his_accounts(self):
        with self._patch_fetch_ads([self._ad_values()]):
            self.social_account_id._sync_ads()
        other_user = self._create_social_media_user(login="ads_user_test")
        self.assertFalse(
            self.SocialAdvertisingAd.with_user(other_user).search(
                [("account_id", "=", self.social_account_id.id)]
            ),
            msg="The ads are scoped by the responsible of the account.",
        )
