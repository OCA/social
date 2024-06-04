# Copyright 2022-2023 Moduon Team S.L. <info@moduon.team>
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

import freezegun
from lxml import html

from odoo.exceptions import UserError
from odoo.tests import tagged

from odoo.addons.mail.tests.common import MailCommon


class MailPostDeferCommon(MailCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls._create_portal_user()
        # Notify employee by email
        cls.user_employee.notification_type = "email"


@freezegun.freeze_time("2023-01-02 10:00:00")
class MessagePostCase(MailPostDeferCommon):
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

    def test_model_without_threading(self):
        """When models don't inherit from mail.thread, they still work."""
        self.partner_portal.email = "portal@example.com"
        with self.mock_mail_gateway():
            self.env["mail.thread"].with_context(
                mail_notify_author=True
            ).message_notify(
                author_id=self.partner_employee.id,
                body="test body",
                model="res.country",
                partner_ids=(self.partner_employee | self.partner_portal).ids,
                res_id=self.ref("base.es"),
            )
            self.assertNoMail(self.partner_employee | self.partner_portal)
            # One minute later, the cron sends the mail
            with freezegun.freeze_time("2023-01-02 10:01:00"):
                self.env["mail.message.schedule"]._send_notifications_cron()
                self.env["mail.mail"].process_email_queue()
                self.assertMailMail(
                    self.partner_portal,
                    "sent",
                    author=self.partner_employee,
                    content="test body",
                )
                self.assertMailMail(
                    self.partner_employee,
                    "sent",
                    author=self.partner_employee,
                    content="test body",
                )
        # Safety belt to avoid false positives in this test
        self.assertFalse(hasattr(self.env["res.country"], "_notify_thread"))
        self.assertTrue(hasattr(self.env["res.partner"], "_notify_thread"))

    def test_button_access(self):
        """A button is added to the email to access the record."""
        customer = self.env["res.partner"].create(
            {"name": "Customer", "email": "customer@example.com"}
        )
        with self.mock_mail_gateway():
            customer.message_post(
                body="test body",
                subject="test subject",
                message_type="comment",
                partner_ids=(self.partner_employee | customer).ids,
            )
            self.assertNoMail(self.partner_employee | customer)
            # After a minute, mails are sent
            with freezegun.freeze_time("2023-01-02 10:01:00"):
                self.env["mail.message.schedule"]._send_notifications_cron()
                self.env["mail.mail"].process_email_queue()
                # Employee has a button that grants them access
                customer_link = customer._notify_get_action_link("view")
                employee_mail = self.assertSentEmail(
                    self.env.user.partner_id,
                    self.partner_employee,
                    body_content="test body",
                )
                self.assertEqual(
                    html.fromstring(employee_mail["body"])
                    .xpath(f"//a[contains(@href, '{customer_link}')]")[0]
                    .text_content()
                    .strip(),
                    "View Contact",
                )
                # Customer got the mail, but doesn't have access
                customer_mail = self.assertSentEmail(
                    self.env.user.partner_id,
                    customer,
                    body_content="test body",
                )
                self.assertFalse(
                    html.fromstring(customer_mail["body"]).xpath(
                        f"//a[contains(@href, '{customer_link}')]"
                    )
                )


@tagged("-at_install", "post_install")
@freezegun.freeze_time("2023-01-02 10:00:00")
class AutomaticNotificationCase(MailPostDeferCommon):
    """Check that automatic notifications are queued too.

    This is a separate case because some notifications require a
    completely-loaded registry, so this case needs to run in post-install mode.
    """

    def test_assignation_mail(self):
        """When assigning a record to a user, a notification is scheduled."""
        with self.mock_mail_gateway():
            self.partner_portal.user_id = self.user_employee.id
            self.partner_portal.flush_recordset()
            self.assertNoMail(self.partner_employee)
            schedules = self.env["mail.message.schedule"].search(
                [
                    ("mail_message_id.res_id", "=", self.partner_portal.id),
                    ("mail_message_id.model", "=", "res.partner"),
                    ("scheduled_datetime", "=", "2023-01-02 10:00:30"),
                ]
            )
            self.assertEqual(len(schedules), 1)
            # After a minute, the mail is sent
            with freezegun.freeze_time("2023-01-02 10:01:00"):
                self.env["mail.message.schedule"]._send_notifications_cron()
                self.assertMailMail(
                    self.partner_employee,
                    "outgoing",
                    author=self.env.user.partner_id,
                    content="You have been assigned to the Contact Chell Gladys.",
                )
