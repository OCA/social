# Copyright 2015 Therp BV <http://therp.nl>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
import psycopg2.errors

from odoo.tests.common import TransactionCase
from odoo.tools import mute_logger

from odoo.addons.mail_follower_custom_notification import uninstall_hook


class TestMailFollowerCustomNotification(TransactionCase):
    def test_mail_follower_custom_notification(self):
        partner = self.env["res.partner"].create(
            {
                "name": "I'm followed",
            }
        )
        demo_user = self.env.ref("base.user_demo")
        mt_comment = self.env.ref("mail.mt_comment")
        mt_comment.mail_follower_custom_notification = "email_and_inbox"
        partner.message_subscribe(demo_user.partner_id.ids)

        message = partner.message_post(
            body="hello world", message_type="comment", subtype_xmlid="mail.mt_comment"
        )
        notifications = self.env["mail.notification"].search(
            [("mail_message_id", "=", message.id)]
        )
        self.assertTrue(
            notifications.filtered(
                lambda x: x.res_partner_id == demo_user.partner_id
                and x.notification_type == "email"
            )
        )
        self.assertTrue(
            notifications.filtered(
                lambda x: x.res_partner_id == demo_user.partner_id
                and x.notification_type == "inbox"
            )
        )

        follower = partner.message_follower_ids.filtered(
            lambda x: x.partner_id == demo_user.partner_id
        )
        follower.mail_follower_custom_notification = {mt_comment.id: "email"}

        message = partner.message_post(
            body="hello world2", message_type="comment", subtype_xmlid="mail.mt_comment"
        )
        notifications = self.env["mail.notification"].search(
            [("mail_message_id", "=", message.id)]
        )
        self.assertTrue(
            notifications.filtered(
                lambda x: x.res_partner_id == demo_user.partner_id
                and x.notification_type == "email"
            )
        )
        self.assertFalse(
            notifications.filtered(
                lambda x: x.res_partner_id == demo_user.partner_id
                and x.notification_type == "inbox"
            )
        )

        follower.mail_follower_custom_notification = False
        uninstall_hook(self.env.cr, self.env.registry)

        with self.assertRaises(psycopg2.errors.UniqueViolation), mute_logger(
            "odoo.sql_db"
        ):
            partner.message_post(
                body="hello world3",
                message_type="comment",
                subtype_xmlid="mail.mt_comment",
            )
