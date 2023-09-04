# Copyright 2022-2023 Moduon Team S.L. <info@moduon.team>
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

import freezegun

from odoo.exceptions import UserError

from odoo.addons.mail.tests.common import MailCommon


@freezegun.freeze_time("2023-01-02 10:00:00")
class MessagePostCase(MailCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls._create_portal_user()
        # Notify employee by email
        cls.user_employee.notification_type = "email"

    def test_standard(self):
        """A normal call just uses the queue by default."""
        with self.mock_mail_gateway():
            msg = self.partner_portal.message_post(
                body="test body",
                subject="test subject",
                message_type="comment",
                partner_ids=self.partner_employee.ids,
            )
            schedules = self.env["mail.message.schedule"].search(
                [
                    ("mail_message_id", "=", msg.id),
                    ("scheduled_datetime", "=", "2023-01-02 10:00:30"),
                ]
            )
            self.assertEqual(len(schedules), 1)
            self.assertNoMail(self.partner_employee)

    def test_forced_arg(self):
        """A forced send via method argument is sent directly."""
        with self.mock_mail_gateway():
            self.partner_portal.message_post(
                body="test body",
                subject="test subject",
                message_type="comment",
                partner_ids=self.partner_employee.ids,
                force_send=True,
            )
            self.assertMailMail(
                self.partner_employee,
                "sent",
                author=self.env.user.partner_id,
                content="test body",
                fields_values={"scheduled_date": False},
            )

    def test_forced_context(self):
        """A forced send via context is sent directly."""
        with self.mock_mail_gateway():
            self.partner_portal.with_context(mail_notify_force_send=True).message_post(
                body="test body",
                subject="test subject",
                message_type="comment",
                partner_ids=self.partner_employee.ids,
            )
            self.assertMailMail(
                self.partner_employee,
                "sent",
                author=self.env.user.partner_id,
                content="test body",
                fields_values={"scheduled_date": False},
            )

    def test_msg_edit(self):
        """Can update messages.

        Upstream Odoo allows only updating notes, regardless of their sent
        status. We allow updating any message that is not sent yet.
        """
        with self.mock_mail_gateway():
            msg = self.partner_portal.message_post(
                body="test body",
                subject="test subject",
                message_type="comment",
                partner_ids=self.partner_employee.ids,
                subtype_xmlid="mail.mt_comment",
            )
            schedules = self.env["mail.message.schedule"].search(
                [
                    ("mail_message_id", "=", msg.id),
                    ("scheduled_datetime", "=", "2023-01-02 10:00:30"),
                ]
            )
            self.assertEqual(len(schedules), 1)
            self.assertNoMail(self.partner_employee)
            # After 15 seconds, the user updates the message
            with freezegun.freeze_time("2023-01-02 10:00:15"):
                self.partner_portal._message_update_content(msg, "new body")
                schedules = self.env["mail.message.schedule"].search(
                    [
                        ("mail_message_id", "=", msg.id),
                        ("scheduled_datetime", "=", "2023-01-02 10:00:45"),
                    ]
                )
                self.assertEqual(len(schedules), 1)
                self.assertNoMail(self.partner_employee)
            # After a minute, the mail is created
            with freezegun.freeze_time("2023-01-02 10:01:00"):
                self.env["mail.message.schedule"]._send_notifications_cron()
                self.assertMailMail(
                    self.partner_employee,
                    "outgoing",
                    author=self.env.user.partner_id,
                    content="new body",
                )

    def test_queued_msg_delete(self):
        """A user can delete a message before it's sent."""
        with self.mock_mail_gateway():
            msg = self.partner_portal.message_post(
                body="test body",
                subject="test subject",
                message_type="comment",
                partner_ids=self.partner_employee.ids,
                subtype_xmlid="mail.mt_comment",
            )
            schedules = self.env["mail.message.schedule"].search(
                [
                    ("mail_message_id", "=", msg.id),
                    ("scheduled_datetime", "=", "2023-01-02 10:00:30"),
                ]
            )
            self.assertEqual(len(schedules), 1)
            # Emulate user clicking on delete button and going through the
            # `/mail/message/update_content` controller
            self.partner_portal._message_update_content(msg, "", [])
            self.env.flush_all()
            self.assertFalse(schedules.exists())
            self.assertNoMail(
                self.partner_employee,
                author=self.env.user.partner_id,
            )
            # One minute later, the cron has no mails to send
            with freezegun.freeze_time("2023-01-02 10:01:00"):
                self.env["mail.message.schedule"]._send_notifications_cron()
                self.env["mail.mail"].process_email_queue()
                self.assertNoMail(
                    self.partner_employee,
                    author=self.env.user.partner_id,
                )

    def test_no_sent_msg_delete(self):
        """A user cannot delete a message after it's sent.

        Usually, the trash button will be hidden in UI if the message is sent.
        However, the server-side protection is still important, because there
        can be a race condition when the mail is sent in the background but
        the user didn't refresh the view.
        """
        with self.mock_mail_gateway():
            msg = self.partner_portal.message_post(
                body="test body",
                subject="test subject",
                message_type="comment",
                partner_ids=self.partner_employee.ids,
                subtype_xmlid="mail.mt_comment",
            )
            # One minute later, the cron sends the mail
            with freezegun.freeze_time("2023-01-02 10:01:00"):
                self.env["mail.message.schedule"]._send_notifications_cron()
                self.env["mail.mail"].process_email_queue()
                self.assertMailMail(
                    self.partner_employee,
                    "sent",
                    author=self.env.user.partner_id,
                    content="test body",
                )
                # Emulate user clicking on delete button and going through the
                # `/mail/message/update_content` controller
                with self.assertRaises(UserError):
                    self.partner_portal._message_update_content(msg, "", [])
