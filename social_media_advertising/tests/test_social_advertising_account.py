# Copyright 2026 Binhex <https://www.binhex.cloud>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from unittest.mock import patch

import psycopg2

from odoo import Command
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tests import tagged
from odoo.tools import mute_logger

from .test_social_advertising_common import (
    PATCH_ADVERTISING_ACCOUNT,
    TestSocialAdvertisingCommon,
)


class TestSocialAdvertisingAccount(TestSocialAdvertisingCommon):
    """Advertising accounts mirrored from the social media."""

    def _patch_fetch(self, values):
        return patch(
            PATCH_ADVERTISING_ACCOUNT.format("_fetch_advertising_accounts"),
            autospec=True,
            return_value=values,
        )

    def _values(self, remote_ref, **values):
        return dict(
            {
                "name": f"Account {remote_ref}",
                "remote_ref": remote_ref,
                "environment": "test",
            },
            **values,
        )

    def test_fetch_advertising_accounts_default(self):
        self.assertEqual(self.social_account_id._fetch_advertising_accounts(), [])

    def test_sync_creates_the_advertising_accounts(self):
        with self._patch_fetch([self._values("urn:ad:1"), self._values("urn:ad:2")]):
            advertising_accounts = self.social_account_id._sync_advertising_accounts()
        self.assertEqual(len(advertising_accounts), 2)
        self.assertTrue(all(advertising_accounts.mapped("last_sync_date")))

    def test_sync_updates_without_duplicating(self):
        with self._patch_fetch([self._values("urn:ad:1")]):
            self.social_account_id._sync_advertising_accounts()
        with self._patch_fetch([self._values("urn:ad:1", name="Renamed")]):
            advertising_accounts = self.social_account_id._sync_advertising_accounts()
        self.assertEqual(len(advertising_accounts), 1)
        self.assertEqual(advertising_accounts.name, "Renamed")

    def test_sync_keeps_the_account_in_use(self):
        """Refreshing the list must not change what the user chose."""
        with self._patch_fetch([self._values("urn:ad:1"), self._values("urn:ad:2")]):
            advertising_accounts = self.social_account_id._sync_advertising_accounts()
        chosen = advertising_accounts.filtered(
            lambda advertising_account: advertising_account.remote_ref == "urn:ad:2"
        )
        chosen.action_set_current()
        with self._patch_fetch([self._values("urn:ad:1"), self._values("urn:ad:2")]):
            self.social_account_id._sync_advertising_accounts()
        self.assertTrue(chosen.is_current)
        self.assertEqual(self.social_account_id.advertising_account_urn, "urn:ad:2")

    def test_sync_drops_the_stale_ones(self):
        with self._patch_fetch([self._values("urn:ad:1"), self._values("urn:ad:2")]):
            self.social_account_id._sync_advertising_accounts()
        with self._patch_fetch([self._values("urn:ad:1")]):
            advertising_accounts = self.social_account_id._sync_advertising_accounts()
        self.assertEqual(advertising_accounts.mapped("remote_ref"), ["urn:ad:1"])

    def test_sync_with_an_empty_answer_drops_nothing(self):
        """An empty answer cannot be told apart from a transient failure."""
        with self._patch_fetch([self._values("urn:ad:1")]):
            self.social_account_id._sync_advertising_accounts()
        with self._patch_fetch([]):
            advertising_accounts = self.social_account_id._sync_advertising_accounts()
        self.assertEqual(advertising_accounts.mapped("remote_ref"), ["urn:ad:1"])

    def test_unlinking_the_account_in_use_clears_the_reference(self):
        advertising_account = self._create_advertising_account(remote_ref="urn:ad:1")
        advertising_account.action_set_current()
        self.assertEqual(self.social_account_id.advertising_account_urn, "urn:ad:1")
        advertising_account.unlink()
        self.assertFalse(self.social_account_id.advertising_account_urn)

    def test_set_current_unsets_the_others(self):
        first = self._create_advertising_account(remote_ref="urn:ad:1")
        second = self._create_advertising_account(remote_ref="urn:ad:2")
        first.action_set_current()
        second.action_set_current()
        self.assertFalse(first.is_current)
        self.assertTrue(second.is_current)
        self.assertEqual(self.social_account_id.advertising_account_urn, "urn:ad:2")

    def test_only_one_account_in_use_in_a_single_write(self):
        first = self._create_advertising_account(remote_ref="urn:ad:1")
        second = self._create_advertising_account(remote_ref="urn:ad:2")
        with self.assertRaises(ValidationError):
            (first + second).write({"is_current": True})

    def test_only_one_account_in_use_in_two_writes(self):
        first = self._create_advertising_account(remote_ref="urn:ad:1")
        second = self._create_advertising_account(remote_ref="urn:ad:2")
        first.write({"is_current": True})
        with self.assertRaises(ValidationError):
            second.write({"is_current": True})

    def test_the_account_in_use_follows_the_environment(self):
        advertising_account = self._create_advertising_account(
            remote_ref="urn:ad:1", environment="production"
        )
        with self.assertRaises(ValidationError):
            advertising_account.write({"is_current": True})

    def test_another_social_account_may_have_its_own(self):
        """The rule is per social media account, not global."""
        other_account = self.SocialAccount.create(
            {"name": "Other account", "media_id": self.social_media_id.id}
        )
        first = self._create_advertising_account(remote_ref="urn:ad:1")
        second = self._create_advertising_account(
            account=other_account, remote_ref="urn:ad:1"
        )
        first.action_set_current()
        second.action_set_current()
        self.assertTrue(first.is_current)
        self.assertTrue(second.is_current)

    def test_get_advertising_account_is_scoped_to_its_social_account(self):
        """Two social accounts may carry the same remote reference."""
        other_account = self.SocialAccount.create(
            {"name": "Other account", "media_id": self.social_media_id.id}
        )
        own = self._create_advertising_account(remote_ref="urn:ad:1")
        self._create_advertising_account(account=other_account, remote_ref="urn:ad:1")
        self.assertEqual(
            self.social_account_id._get_advertising_account("urn:ad:1"), own
        )

    def test_get_advertising_account_of_an_unknown_reference_is_empty(self):
        self._create_advertising_account(remote_ref="urn:ad:1")
        self.assertFalse(self.social_account_id._get_advertising_account("urn:ad:404"))

    @mute_logger("odoo.sql_db")
    def test_remote_ref_is_unique_per_account(self):
        self._create_advertising_account(remote_ref="urn:ad:1")
        with self.assertRaises(psycopg2.IntegrityError):
            with self.env.cr.savepoint():
                self._create_advertising_account(remote_ref="urn:ad:1")

    def test_display_name_shows_the_reference(self):
        """The generic module shows the remote reference as it is.

        Shortening it belongs to the connector, which overrides
        ``_get_display_reference()`` with the format of its social media.
        """
        advertising_account = self._create_advertising_account(
            name="Dunder Mifflin", remote_ref="urn:li:sponsoredAccount:123"
        )
        self.assertEqual(
            advertising_account.display_name,
            "Dunder Mifflin (urn:li:sponsoredAccount:123)",
        )

    def test_web_url_is_empty_without_a_connector(self):
        advertising_account = self._create_advertising_account(remote_ref="urn:ad:1")
        self.assertFalse(advertising_account.web_url)

    def test_action_sync_without_a_connector(self):
        res = self.social_account_id.action_sync_advertising_accounts()
        self.assertFalse(res["success"])
        self.assertEqual(res["accounts"], 0)

    def test_action_sync_notify_without_a_connector(self):
        res = self.social_account_id.action_sync_advertising_accounts_notify()
        self.assertEqual(res["tag"], "display_notification")
        self.assertEqual(res["params"]["type"], "danger")

    def test_action_sync_notify_success(self):
        with patch(
            PATCH_ADVERTISING_ACCOUNT.format("_advertising_media_types"),
            autospec=True,
            return_value=[self.social_account_id.media_type],
        ), self._patch_fetch([self._values("urn:ad:1")]):
            self.social_account_id.invalidate_recordset()
            res = self.social_account_id.action_sync_advertising_accounts_notify()
        self.assertEqual(res["params"]["type"], "success")

    def test_action_sync_reports_the_error(self):
        with patch(
            PATCH_ADVERTISING_ACCOUNT.format("_advertising_media_types"),
            autospec=True,
            return_value=[self.social_account_id.media_type],
        ), patch(
            PATCH_ADVERTISING_ACCOUNT.format("_fetch_advertising_accounts"),
            autospec=True,
            side_effect=UserError("Boom"),
        ):
            self.social_account_id.invalidate_recordset()
            res = self.social_account_id.action_sync_advertising_accounts_notify()
        self.assertEqual(res["params"]["type"], "danger")
        self.assertIn("Boom", res["params"]["message"])

    def test_campaign_counts_only_its_own(self):
        """The counters follow the stored link, not the account in use."""
        first = self._create_advertising_account(remote_ref="urn:ad:1")
        second = self._create_advertising_account(remote_ref="urn:ad:2")
        self.campaign_id.write({"advertising_account_id": first.id})
        self.campaign_group_id.write({"advertising_account_id": first.id})
        self.assertEqual(first.campaign_count, 1)
        self.assertEqual(first.campaign_group_count, 1)
        self.assertEqual(second.campaign_count, 0)
        self.assertEqual(second.campaign_group_count, 0)
        second.action_set_current()
        first.invalidate_recordset()
        second.invalidate_recordset()
        self.assertEqual(
            first.campaign_count,
            1,
            msg="Choosing another advertising account must not move the "
            "campaigns already linked.",
        )
        self.assertEqual(second.campaign_count, 0)

    def test_open_campaigns_is_scoped(self):
        advertising_account = self._create_advertising_account(remote_ref="urn:ad:1")
        self.campaign_id.write({"advertising_account_id": advertising_account.id})
        action = advertising_account.action_open_campaigns()
        self.assertEqual(action["res_model"], "social.advertising.campaign")
        self.assertEqual(
            action["domain"], [("advertising_account_id", "=", advertising_account.id)]
        )
        campaigns = self.SocialAdvertisingCampaign.search(action["domain"])
        self.assertEqual(campaigns, self.campaign_id)

    def test_open_campaign_groups_is_scoped(self):
        advertising_account = self._create_advertising_account(remote_ref="urn:ad:1")
        self.campaign_group_id.write({"advertising_account_id": advertising_account.id})
        action = advertising_account.action_open_campaign_groups()
        self.assertEqual(action["res_model"], "social.advertising.campaign.group")
        groups = self.SocialAdvertisingCampaignGroup.search(action["domain"])
        self.assertEqual(groups, self.campaign_group_id)

    def test_unlinking_keeps_the_campaign(self):
        """Dropping a stale advertising account must not delete history."""
        advertising_account = self._create_advertising_account(remote_ref="urn:ad:1")
        self.campaign_id.write({"advertising_account_id": advertising_account.id})
        advertising_account.unlink()
        self.assertTrue(self.campaign_id.exists())
        self.assertFalse(self.campaign_id.advertising_account_id)


@tagged("post_install", "-at_install")
class TestSocialAdvertisingAccountSecurity(TestSocialAdvertisingCommon):
    """Access rights and record rules of the advertising accounts.

    Users are created here, so every module has to be in the registry.
    """

    def _patch_fetch(self, values):
        return patch(
            PATCH_ADVERTISING_ACCOUNT.format("_fetch_advertising_accounts"),
            autospec=True,
            return_value=values,
        )

    def test_set_current_requires_managing_the_account(self):
        advertising_account = self._create_advertising_account(remote_ref="urn:ad:1")
        other_user = self._create_social_media_user(login="advertising_other_user")
        with self.assertRaises(AccessError):
            advertising_account.with_user(other_user).action_set_current()

    def test_user_reads_but_does_not_write(self):
        advertising_account = self._create_advertising_account(remote_ref="urn:ad:1")
        user = self._create_social_media_user(login="advertising_reader")
        self.social_account_id.write({"user_id": user.id})
        advertising_account.with_user(user).read(["name"])
        with self.assertRaises(AccessError):
            advertising_account.with_user(user).write({"name": "Hacked"})

    def test_manager_writes(self):
        advertising_account = self._create_advertising_account(remote_ref="urn:ad:1")
        manager = self._create_social_media_manager(login="advertising_writer")
        advertising_account.with_user(manager).write({"name": "Renamed"})
        self.assertEqual(advertising_account.name, "Renamed")

    def test_user_only_sees_the_accounts_he_is_responsible_for(self):
        advertising_account = self._create_advertising_account(remote_ref="urn:ad:1")
        other_user = self._create_social_media_user(login="advertising_stranger")
        self.assertFalse(
            advertising_account.with_user(other_user).search(
                [("id", "=", advertising_account.id)]
            )
        )

    def test_a_regular_user_synchronizes_his_own_account(self):
        """The contract the ``sudo()`` of the synchronization is written for.

        A social media user reads the advertising accounts and never writes
        them, and the refresh runs from his own social media account.
        """
        user = self._create_social_media_user(login="advertising_syncer")
        self.social_account_id.write({"user_id": user.id})
        account = self.social_account_id.with_user(user)
        with self._patch_fetch(
            [
                {
                    "name": "Fetched account",
                    "remote_ref": "urn:ad:1",
                    "environment": self.social_account_id.environment,
                }
            ]
        ):
            advertising_accounts = account._sync_advertising_accounts()
        self.assertEqual(advertising_accounts.remote_ref, "urn:ad:1")
        self.assertTrue(
            advertising_accounts.is_current,
            msg="The only candidate is chosen, which is also written sudoed.",
        )

    def test_another_company_sees_neither_the_account_nor_its_ads(self):
        """Both models are filtered by the company of their social account.

        ``company_id`` is a stored related field of the social media
        account, and the two multi-company rules lean on it.
        """
        other_company = self.env["res.company"].create({"name": "Another company"})
        user = self._create_social_media_user(login="advertising_other_company")
        self.social_account_id.write({"user_id": user.id})
        advertising_account = self._create_advertising_account(remote_ref="urn:ad:1")
        ad = self.env["social.advertising.ad"].create(
            {
                "remote_ref": "urn:ad:creative:1",
                "account_id": self.social_account_id.id,
                "advertising_account_id": advertising_account.id,
            }
        )
        self.assertTrue(advertising_account.with_user(user).search([]))
        self.social_account_id.write({"company_id": other_company.id})
        self.assertEqual(advertising_account.company_id, other_company)
        self.assertEqual(ad.company_id, other_company)
        self.assertFalse(
            advertising_account.with_user(user).search([]),
            msg="The company of the account is none of the allowed ones.",
        )
        self.assertFalse(ad.with_user(user).search([]))
        user.write({"company_ids": [Command.link(other_company.id)]})
        allowed = self.env(
            user=user,
            context=dict(
                self.env.context,
                allowed_company_ids=(self.env.company + other_company).ids,
            ),
        )
        self.assertTrue(
            advertising_account.with_env(allowed).search([]),
            msg="The company of the account is one of the allowed ones now.",
        )
        self.assertTrue(ad.with_env(allowed).search([]))

    def test_user_cannot_unlink_a_campaign_group_nor_a_tag(self):
        """Both are shared data every user creates but nobody deletes."""
        user = self._create_social_media_user(login="advertising_deleter")
        tag = self.SocialTag.create({"name": "Promo"})
        with self.assertRaises(AccessError):
            self.campaign_group_id.with_user(user).unlink()
        with self.assertRaises(AccessError):
            tag.with_user(user).unlink()
