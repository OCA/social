# Copyright 2026 Binhex <https://www.binhex.cloud>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from datetime import timedelta
from unittest.mock import patch

from freezegun import freeze_time

from odoo import _, fields
from odoo.exceptions import AccessError, UserError
from odoo.fields import Command
from odoo.tests.common import tagged
from odoo.tools import mute_logger

from odoo.addons.social_media_base.exceptions import SocialCredentialsError
from odoo.addons.social_media_base.hooks import remove_social_media
from odoo.addons.social_media_base.tests.test_social_common import (
    TestSocialMediaBaseCommon,
)

from .test_social_common import PATCH_ACCOUNT, PATCH_WIZARD_ACCOUNT

LOGGER_ACCOUNT = "odoo.addons.social_media_base.models.social_account"


class TestSocialAccountBase(TestSocialMediaBaseCommon):
    def test_compute_display_name(self):
        self.social_account_id._compute_display_name()
        self.assertEqual(self.social_account_id.display_name, "Linkedin")

    def test_archive_account(self):
        self.social_account_id.action_archive_account()
        self.assertFalse(self.social_post_id.active)
        self.assertFalse(self.social_post_account_id.active)
        self.assertFalse(self.social_account_id.active)

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

    def test_check_can_associate_other_company(self):
        other_company = self.env["res.company"].create({"name": "Another company"})
        self.env.user.write({"company_ids": [(3, other_company.id)]})
        self.social_account_id.write({"company_id": other_company.id})
        with self.assertRaises(AccessError):
            self.social_account_id._check_can_associate()

    def test_purge_account(self):
        post = self.social_post_id
        post_account = self.social_post_account_id
        self.social_account_id.action_archive_account()
        action = self.social_account_id.action_purge_account()
        self.assertEqual(action.get("res_model"), "social.account")
        self.assertEqual(action.get("target"), "main")
        self.assertFalse(self.social_account_id.exists())
        self.assertFalse(post_account.exists())
        self.assertFalse(post.exists())

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
            self.SocialAccount._remove_social_media("other_social")
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
        self.social_account_id.write({"active": False})
        self.assertFalse(self.social_account_id.active)
        self.assertFalse(self.social_post_id.active)
        self.assertFalse(self.social_post_account_id.active)
        self.social_account_id.write({"active": True})
        self.assertTrue(self.social_account_id.active)
        self.assertTrue(self.social_post_id.active)
        self.assertTrue(self.social_post_account_id.active)

    def test_archive_cascade_with_several_accounts(self):
        """A post is archived once no active account is left, not before."""
        other_account = self.SocialAccount.create(
            {"name": "Other Linkedin", "media_id": self.social_media_id.id}
        )
        self.social_post_id.write({"account_ids": [Command.link(other_account.id)]})
        self.social_account_id.write({"active": False})
        self.assertTrue(self.social_post_id.active)
        self.assertFalse(self.social_post_account_id.active)
        other_account.write({"active": False})
        self.assertFalse(self.social_post_id.active)

    def test_archive_cascade_with_the_accounts_archived_at_once(self):
        other_account = self.SocialAccount.create(
            {"name": "Other Linkedin", "media_id": self.social_media_id.id}
        )
        self.social_post_id.write({"account_ids": [Command.link(other_account.id)]})
        (self.social_account_id + other_account).write({"active": False})
        self.assertFalse(self.social_post_id.active)

    def test_unarchive_sends_the_overdue_scheduled_posts_to_draft(self):
        """Reactivating must not hand an already due post to the cron."""
        post = self.social_post_id
        post.write({"send_post": "schedule"})
        post.send_post_date = fields.Datetime.now() + timedelta(minutes=5)
        self.assertEqual(post.state, "planned")
        self.social_account_id.write({"active": False})
        with freeze_time(fields.Datetime.now() + timedelta(minutes=10)):
            self.social_account_id.write({"active": True})
        self.assertTrue(post.active)
        self.assertEqual(post.state, "draft")
        self.assertTrue(
            post.message_ids.filtered(
                lambda message: "set back to draft" in (message.body or "")
            )
        )

    def test_unarchive_keeps_the_posts_scheduled_in_the_future(self):
        post = self.social_post_id
        post.write({"send_post": "schedule"})
        post.send_post_date = fields.Datetime.now() + timedelta(hours=2)
        self.social_account_id.write({"active": False})
        self.social_account_id.write({"active": True})
        self.assertEqual(post.state, "planned")

    def test_archive_post_cascades_to_its_publications(self):
        self.social_post_id.write({"active": False})
        self.assertFalse(self.social_post_account_id.active)
        self.social_post_id.write({"active": True})
        self.assertTrue(self.social_post_account_id.active)

    def test_unarchive_post_keeps_the_lines_of_an_archived_account(self):
        """The account is what hides those lines, not the post."""
        other_account = self.SocialAccount.create(
            {"name": "Other Linkedin", "media_id": self.social_media_id.id}
        )
        other_line = self.SocialPostAccount.create(
            {
                "post_id": self.social_post_id.id,
                "account_id": other_account.id,
                "message": "Test message",
            }
        )
        self.social_post_id.write({"account_ids": [Command.link(other_account.id)]})
        other_account.write({"active": False})
        self.assertFalse(other_line.active)
        self.social_post_id.write({"active": False})
        self.social_post_id.write({"active": True})
        self.assertTrue(self.social_post_account_id.active)
        self.assertFalse(other_line.active)

    def test_action_unarchive_account(self):
        self.social_account_id.action_archive_account()
        self.assertFalse(self.social_account_id.active)
        self.social_account_id.action_unarchive_account()
        self.assertTrue(self.social_account_id.active)
        self.assertTrue(self.social_post_id.active)
        self.assertTrue(self.social_post_account_id.active)

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

    def test_need_update(self):
        Bus = self.env["bus.bus"]
        with patch.object(type(Bus), "_sendone", autospec=True) as patch_sendone:
            self.social_account_id._need_update()
            patch_sendone.assert_called_once()

    def test_need_update_notifies_the_responsible_user(self):
        Bus = self.env["bus.bus"]
        self.social_account_id.user_id = self.env.ref("base.user_admin")
        with patch.object(type(Bus), "_sendone", autospec=True) as patch_sendone:
            self.social_account_id._need_update()
        self.assertEqual(
            patch_sendone.call_args[0][1], self.social_account_id.user_id.partner_id
        )

    def test_need_update_names_the_accounts(self):
        """The dashboard has to say which account to act on.

        A user responsible for several accounts on several social media can do
        nothing with a notice that only says something needs updating.
        """
        Bus = self.env["bus.bus"]
        with patch.object(type(Bus), "_sendone", autospec=True) as patch_sendone:
            self.social_account_id._need_update()
        self.assertEqual(
            patch_sendone.call_args[0][3]["accounts"],
            [
                {
                    "id": self.social_account_id.id,
                    "name": self.social_account_id.name,
                    "media": self.social_account_id.media_id.name,
                }
            ],
        )

    def test_need_update_without_accounts(self):
        Bus = self.env["bus.bus"]
        with patch.object(type(Bus), "_sendone", autospec=True) as patch_sendone:
            self.SocialAccount._need_update()
        self.assertEqual(patch_sendone.call_args[0][1], self.env.user.partner_id)

    def test_clear_credentials_flag_takes_the_warning_down(self):
        """A new authorization is what the flag always promised would clear it.

        Nothing in base used to do it: the flag only ever went down as a side
        effect of the import, which is not base's any more.
        """
        self.social_account_id.need_update = True
        Bus = self.env["bus.bus"]
        with patch.object(type(Bus), "_sendone", autospec=True) as patch_sendone:
            self.social_account_id._clear_credentials_flag()
        self.assertFalse(self.social_account_id.need_update)
        self.assertFalse(patch_sendone.call_args[0][3]["need_update"])

    def test_clear_credentials_flag_says_nothing_when_it_was_down(self):
        """An account nobody flagged has no warning to take down."""
        self.social_account_id.need_update = False
        Bus = self.env["bus.bus"]
        with patch.object(type(Bus), "_sendone", autospec=True) as patch_sendone:
            self.social_account_id._clear_credentials_flag()
        patch_sendone.assert_not_called()

    def test_refresh_credentials_is_not_available_by_default(self):
        self.assertFalse(self.social_account_id._refresh_credentials())

    def test_get_social_dashboard_url(self):
        url = self.SocialAccount._get_social_dashboard_url()
        menu = self.env.ref("social_media_base.social_dashboard_menu")
        self.assertEqual(url, f"/web#menu_id={menu.id}&action={menu.action.id}")

    def test_get_social_dashboard_url_without_action(self):
        menu = self.env.ref("social_media_base.social_dashboard_menu")
        menu.action = False
        self.assertEqual(self.SocialAccount._get_social_dashboard_url(), "/web")

    def test_remove_social_media_uninstall_hook(self):
        with patch(PATCH_ACCOUNT.format("_remove_social_media"), autospec=True) as mock:
            remove_social_media(self.env, "other_social")
        mock.assert_called_once()
        self.assertEqual(mock.call_args[0][1], "other_social")

    def test_the_wizard_hooks_do_nothing_in_the_base_module(self):
        """Every connector fills them in; the base module answers nothing."""
        self.assertIsNone(self.WizardAccount._get_url_redirect())
        self.assertIsNone(self.WizardAccount._action_add_account())
        self.assertIsNone(self.WizardAccount._update_account())
        self.assertIsNone(self.WizardAccount.action_update_account())

    def test_the_validation_hook_accepts_by_default(self):
        self.assertTrue(self.WizardAccount._action_valid_add_account())

    def test_wizard_update_account_clears_the_credentials_flag(self):
        """Re-authorizing is the moment the warning stops being true.

        It is cleared by the generic wrapper and not by ``_update_account``,
        which is a connector hook, so a new connector cannot forget it.
        """
        self.social_account_id.need_update = True
        wizard = self.WizardAccount.create(
            {
                "media_id": self.social_media_id.id,
                "account_id": self.social_account_id.id,
            }
        )
        with patch(PATCH_WIZARD_ACCOUNT.format("_update_account"), autospec=True):
            wizard.action_update_account()
        self.assertFalse(self.social_account_id.need_update)

    def test_wizard_update_account_keeps_the_flag_when_it_fails(self):
        """The credentials did not prove anything, so the warning stays up."""
        self.social_account_id.need_update = True
        wizard = self.WizardAccount.create(
            {
                "media_id": self.social_media_id.id,
                "account_id": self.social_account_id.id,
            }
        )
        with patch(
            PATCH_WIZARD_ACCOUNT.format("_update_account"),
            autospec=True,
            side_effect=ValueError("boom"),
        ), self.assertRaises(UserError):
            wizard.action_update_account()
        self.assertTrue(self.social_account_id.need_update)

    def test_wizard_update_account_wraps_unexpected_errors(self):
        wizard = self.WizardAccount.create(
            {
                "media_id": self.social_media_id.id,
                "account_id": self.social_account_id.id,
            }
        )
        with patch(
            PATCH_WIZARD_ACCOUNT.format("_update_account"),
            autospec=True,
            side_effect=ValueError("boom"),
        ), self.assertRaises(UserError) as capture:
            wizard.action_update_account()
        self.assertIn("boom", str(capture.exception))


@tagged("post_install", "-at_install")
class TestSocialAccountBaseCredentials(TestSocialMediaBaseCommon):
    """The cron walks over the accounts of every connector of the registry."""

    def test_run_check_media_updates_renews_the_credentials(self):
        """The updates cron is also what keeps the tokens from running out."""
        with patch.object(
            type(self.social_account_id),
            "validate_access_token",
            autospec=True,
        ) as mock_validate:
            self.SocialAccount._run_check_media_updates()
        self.assertTrue(mock_validate.called)
        self.assertTrue(
            mock_validate.call_args[0][0].env.context.get("not_notify"),
            "The cron must not notify a user who asked for nothing",
        )

    def test_run_check_media_updates_asks_for_the_domain(self):
        """Which accounts are checked is not decided here any more.

        Base leaves no account out; a module that reads the social media for
        something else is the one that has a reason to, and it says so by
        extending the domain. The domain itself is not asserted here on
        purpose: another module may legitimately have added a clause to it.
        """
        with patch.object(
            type(self.social_account_id),
            "validate_access_token",
            autospec=True,
        ) as mock_validate:
            self.SocialAccount._run_check_media_updates()
        self.assertIn(
            self.social_account_id.id,
            [call[0][0].id for call in mock_validate.call_args_list],
        )

    def _run_check_media_updates_failing_on_the_account(self, error):
        """Run the cron with ``validate_access_token`` raising on one account.

        :return: the other account, which must be checked all the same.
        """
        other_account = self.SocialAccount.create(
            {
                "name": "Other account",
                "media_id": self.social_media_id.id,
                "username": "other_account_check",
            }
        )
        checked = []

        def _validate(account):
            checked.append(account.id)
            if account.id == self.social_account_id.id:
                raise error

        with patch.object(
            type(self.social_account_id),
            "validate_access_token",
            autospec=True,
            side_effect=_validate,
        ):
            self.SocialAccount._run_check_media_updates()
        self.assertIn(other_account.id, checked)
        self.assertFalse(other_account.need_update)
        return other_account

    @mute_logger(LOGGER_ACCOUNT)
    def test_run_check_media_updates_flags_the_account_it_cannot_renew(self):
        self._run_check_media_updates_failing_on_the_account(
            SocialCredentialsError(_("The token was revoked"))
        )
        self.assertTrue(self.social_account_id.need_update)
        self.assertTrue(
            self.social_account_id.message_ids.filtered(
                lambda message: "The token was revoked" in (message.body or "")
            )
        )

    @mute_logger(LOGGER_ACCOUNT)
    def test_run_check_media_updates_does_not_flag_a_transient_failure(self):
        """Only the credentials the social media refused ask for a new
        authorization: nothing clears the flag on its own.
        """
        self._run_check_media_updates_failing_on_the_account(
            ValueError("The social media did not answer")
        )
        self.assertFalse(self.social_account_id.need_update)
        self.assertFalse(
            self.social_account_id.message_ids.filtered(
                lambda message: "no longer valid" in (message.body or "")
            )
        )


@tagged("post_install", "-at_install")
class TestSocialAccountBaseUsers(TestSocialMediaBaseCommon):
    """Users are created here, so every module has to be in the registry."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.User = cls.env["res.users"]

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

    def test_the_record_rule_hides_the_accounts_of_other_users(self):
        """A user only sees the accounts they are responsible for."""
        social_user = self._create_social_media_user()
        self.social_account_id.write({"user_id": self.env.user.id})
        own_account = self.SocialAccount.create(
            {
                "name": "Own account",
                "media_id": self.social_media_id.id,
                "user_id": social_user.id,
            }
        )
        visible = self.SocialAccount.with_user(social_user).search([])
        self.assertIn(own_account, visible)
        self.assertNotIn(self.social_account_id, visible)

    def test_the_record_rule_hides_the_posts_of_other_users(self):
        social_user = self._create_social_media_user()
        self.social_post_id.write({"user_id": self.env.user.id})
        own_post = self.SocialPost.create(
            {
                "message": "Own message",
                "account_ids": [Command.set([self.social_account_id.id])],
                "user_id": social_user.id,
            }
        )
        visible = self.SocialPost.with_user(social_user).search([])
        self.assertIn(own_post, visible)
        self.assertNotIn(self.social_post_id, visible)

    def test_the_record_rule_hides_the_publications_of_other_users(self):
        social_user = self._create_social_media_user()
        self.social_account_id.write({"user_id": self.env.user.id})
        own_account = self.SocialAccount.create(
            {
                "name": "Own account",
                "media_id": self.social_media_id.id,
                "user_id": social_user.id,
            }
        )
        own_publication = self.SocialPostAccount.create(
            {"message": "Own publication", "account_id": own_account.id}
        )
        visible = self.SocialPostAccount.with_user(social_user).search([])
        self.assertIn(own_publication, visible)
        self.assertNotIn(self.social_post_account_id, visible)

    def test_a_manager_sees_the_records_of_every_user(self):
        manager = self._create_social_media_manager()
        self.social_account_id.write({"user_id": self.env.user.id})
        self.social_post_id.write({"user_id": self.env.user.id})
        self.assertIn(
            self.social_account_id, self.SocialAccount.with_user(manager).search([])
        )
        self.assertIn(
            self.social_post_id, self.SocialPost.with_user(manager).search([])
        )
        self.assertIn(
            self.social_post_account_id,
            self.SocialPostAccount.with_user(manager).search([]),
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
            wizard.action_update_account()
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

    def test_post_count(self):
        other_account = self.SocialAccount.create(
            {"name": "Other account", "media_id": self.social_media_id.id}
        )
        self.assertEqual(self.social_account_id.post_count, 1)
        self.assertEqual(other_account.post_count, 0)
        self.SocialPost.create(
            {
                "message": "Another message",
                "account_ids": [Command.set([self.social_account_id.id])],
            }
        )
        self.assertEqual(
            self.social_account_id.post_count,
            2,
            "A new post targeting the account has to invalidate the counter "
            "without waiting for the next request",
        )

    def test_action_open_posts(self):
        action = self.social_account_id.action_open_posts()
        self.assertEqual(action["res_model"], "social.post")
        self.assertEqual(
            action["domain"], [("account_ids", "in", self.social_account_id.ids)]
        )
        self.assertEqual(self.SocialPost.search(action["domain"]), self.social_post_id)


class TestSocialAccountUtmCampaigns(TestSocialMediaBaseCommon):
    """The marketing campaigns reachable from a social media account."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.UtmCampaign = cls.env["utm.campaign"]
        cls.utm_campaign_id = cls.UtmCampaign.create({"name": "Test Utm Campaign"})

    def test_utm_campaign_count_and_action(self):
        # The campaign is set on the post: a publication of a post always
        # carries the campaign of that post.
        self.social_post_id.write({"campaign_id": self.utm_campaign_id.id})
        self.social_account_id.invalidate_recordset()
        self.assertEqual(self.social_account_id.utm_campaign_count, 1)
        action = self.social_account_id.action_open_utm_campaigns()
        self.assertEqual(action["res_model"], "utm.campaign")
        self.assertEqual(
            self.UtmCampaign.search_count(action["domain"]),
            1,
        )

    def test_utm_campaign_count_covers_the_imported_publications(self):
        """A publication imported from the social media has no parent post."""
        imported = self.SocialPostAccount.create(
            {
                "message": "Imported publication",
                "account_id": self.social_account_id.id,
                "campaign_id": self.utm_campaign_id.id,
            }
        )
        self.assertFalse(imported.post_id)
        self.social_account_id.invalidate_recordset()
        self.assertEqual(self.social_account_id.utm_campaign_count, 1)

    def test_utm_campaign_count_covers_the_posts_not_sent_yet(self):
        """A draft post has no publication, but its campaign is already known."""
        draft = self.SocialPost.create(
            {
                "message": "Draft post",
                "account_ids": [Command.set(self.social_account_id.ids)],
                "campaign_id": self.utm_campaign_id.id,
            }
        )
        self.assertEqual(draft.state, "draft")
        self.assertFalse(draft.post_account_ids)
        self.social_account_id.invalidate_recordset()
        self.assertEqual(self.social_account_id.utm_campaign_count, 1)
        action = self.social_account_id.action_open_utm_campaigns()
        self.assertEqual(
            self.UtmCampaign.search(action["domain"]), self.utm_campaign_id
        )

    def test_utm_campaign_count_does_not_count_a_campaign_twice(self):
        """The same campaign on a post and on an imported publication is one."""
        self.social_post_id.write({"campaign_id": self.utm_campaign_id.id})
        self.SocialPostAccount.create(
            {
                "message": "Imported publication",
                "account_id": self.social_account_id.id,
                "campaign_id": self.utm_campaign_id.id,
            }
        )
        self.social_account_id.invalidate_recordset()
        self.assertEqual(self.social_account_id.utm_campaign_count, 1)

    def test_utm_campaign_count_without_campaigns(self):
        self.assertEqual(self.social_account_id.utm_campaign_count, 0)

    def test_utm_campaign_count_ignores_the_other_accounts(self):
        other_account = self.SocialAccount.create(
            {"name": "Other account", "media_id": self.social_media_id.id}
        )
        self.SocialPostAccount.create(
            {
                "message": "Other publication",
                "account_id": other_account.id,
                "campaign_id": self.utm_campaign_id.id,
            }
        )
        self.assertEqual(self.social_account_id.utm_campaign_count, 0)
