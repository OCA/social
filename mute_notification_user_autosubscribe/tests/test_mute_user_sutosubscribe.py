# Copyright 2024 Manuel Regidor <manuel.regidor@sygel.es>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo.tests import new_test_user

from odoo.addons.mail.tests.common import MailCommon


class TestMuteUserAutosubscribe(MailCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user_1 = new_test_user(
            cls.env, login="user_1", groups="base.group_partner_manager,base.group_user"
        )
        cls.user_2 = new_test_user(
            cls.env, login="user_2", groups="base.group_partner_manager,base.group_user"
        )
        cls.user_autosubscribe_mute = cls.env["user.autosubscribe.mute"].create(
            {
                "name": "Mute Contact Notification",
                "model_id": cls.env["ir.model"]._get("res.partner").id,
            }
        )

    def send_email_mute_autosubscribe(cls, doc, user_id, body):
        with cls.mock_mail_gateway():
            return doc.with_user(user_id.id).message_post(
                body=body, subtype_xmlid="mail.mt_comment"
            )

    def test_do_not_mute_user_field(self):
        user_2_partner = self.user_2.partner_id
        # Create new contact with user_1.
        contact = (
            self.env["res.partner"]
            .with_user(self.user_1.id)
            .create({"name": "Contact"})
        )
        # Check user_2 is not subscribed
        self.assertFalse(user_2_partner.id in contact.message_partner_ids.ids)
        # Set user_2 as the Salesperson
        # Check user_2 is now subscribed
        contact.write({"user_id": self.user_2.id})
        self.assertTrue(user_2_partner.id in contact.message_partner_ids.ids)
        # Post message with user_1
        message = self.send_email_mute_autosubscribe(contact, self.user_1, "Test-1")
        # user_2 has been sent a notification
        receivers = message.notification_ids.mapped("res_partner_id")
        self.assertTrue(user_2_partner.id in receivers.ids)

    def test_mute_users_field(self):
        user_2_partner = self.user_2.partner_id
        # Mute user_2 from salesperson autosubscription in res.partner
        self.user_autosubscribe_mute.write({"user_ids": [self.user_2.id]})
        # Create new contact with user_1 and set user_2 and set user_2 as the
        # salesperson
        contact = (
            self.env["res.partner"]
            .with_user(self.user_1.id)
            .create({"name": "Contact", "user_id": self.user_2.id})
        )
        # Check user_2 is subscribed
        self.assertTrue(user_2_partner.id in contact.message_partner_ids.ids)
        # Post message with user_1
        message = self.send_email_mute_autosubscribe(contact, self.user_1, "Test-2")
        # user_2 has NOT been sent a notification
        receivers = message.notification_ids.mapped("res_partner_id")
        self.assertFalse(user_2_partner.id in receivers.ids)
        # user_2 subscription only contains "Mute" subtype
        follower = self.env["mail.followers"].search(
            [
                ("res_model", "=", "res.partner"),
                ("res_id", "=", contact.id),
                ("partner_id", "=", user_2_partner.id),
            ],
            limit=1,
        )
        self.assertEqual(len(follower.subtype_ids), 1)
        self.assertEqual(
            follower.subtype_ids[0],
            self.env.ref("mute_notification_user_autosubscribe.muted"),
        )

    def test_mute_groups_field(self):
        user_2_partner = self.user_2.partner_id
        # Mute group base.group_partner_manager from salesperson
        # autosubscription in res.partner
        self.user_autosubscribe_mute.write(
            {"group_ids": [self.env.ref("base.group_partner_manager").id]}
        )
        # Create new contact with user_1 and set user_2 and set user_2 as the
        # salesperson
        contact = (
            self.env["res.partner"]
            .with_user(self.user_1.id)
            .create({"name": "Contact", "user_id": self.user_2.id})
        )
        # Check user_2 is subscribed
        self.assertTrue(user_2_partner.id in contact.message_partner_ids.ids)
        # Post message with user_1
        message = self.send_email_mute_autosubscribe(contact, self.user_1, "Test-2")
        # user_2 has NOT been sent a notification
        receivers = message.notification_ids.mapped("res_partner_id")
        self.assertFalse(user_2_partner.id in receivers.ids)
        # user_2 subscription only contains "Mute" subtype
        follower = self.env["mail.followers"].search(
            [
                ("res_model", "=", "res.partner"),
                ("res_id", "=", contact.id),
                ("partner_id", "=", user_2_partner.id),
            ],
            limit=1,
        )
        self.assertEqual(len(follower.subtype_ids), 1)
        self.assertEqual(
            follower.subtype_ids[0],
            self.env.ref("mute_notification_user_autosubscribe.muted"),
        )
