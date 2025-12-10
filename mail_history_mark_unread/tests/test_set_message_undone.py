# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from unittest.mock import patch

from odoo.addons.base.tests.common import SavepointCaseWithUserDemo


class TestSetMessageUndone(SavepointCaseWithUserDemo):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner = cls.env["res.partner"].create({"name": "Test Partner"})

    def test_01_set_message_undone_marks_notification_unread_and_sends_bus(self):
        message = self.env["mail.message"].create(
            {
                "model": "res.partner",
                "res_id": self.partner.id,
                "body": "message in history",
                "message_type": "comment",
                "subtype_id": self.env.ref("mail.mt_comment").id,
            }
        )
        notification = self.env["mail.notification"].create(
            {
                "mail_message_id": message.id,
                "notification_status": "sent",
                "notification_type": "inbox",
                "res_partner_id": self.env.user.partner_id.id,
                "is_read": True,
            }
        )
        self.assertTrue(notification.is_read)

        with patch.object(
            type(self.env["bus.bus"]), "_sendone", autospec=True
        ) as mocked_sendone:
            message.set_message_undone()

            notification.invalidate_recordset(["is_read"])
            self.assertFalse(notification.is_read)

            expected_counter = self.env.user.partner_id._get_needaction_count()
            mocked_sendone.assert_called_once()
            _self, target, notification_type, payload = mocked_sendone.call_args.args
            self.assertEqual(target, self.env.user.partner_id)
            self.assertEqual(notification_type, "mail.message/mark_as_unread")
            self.assertEqual(payload.get("message_ids"), [message.id])
            self.assertEqual(payload.get("needaction_inbox_counter"), expected_counter)

    def test_02_set_message_undone_noop_when_no_read_notification(self):
        message = self.env["mail.message"].create(
            {
                "model": "res.partner",
                "res_id": self.partner.id,
                "body": "message without read notification",
                "message_type": "comment",
                "subtype_id": self.env.ref("mail.mt_comment").id,
            }
        )
        # Notification exists but is already unread
        self.env["mail.notification"].create(
            {
                "mail_message_id": message.id,
                "notification_status": "sent",
                "notification_type": "inbox",
                "res_partner_id": self.env.user.partner_id.id,
                "is_read": False,
            }
        )

        with patch.object(
            type(self.env["bus.bus"]), "_sendone", autospec=True
        ) as mocked_sendone:
            message.set_message_undone()
            mocked_sendone.assert_not_called()
