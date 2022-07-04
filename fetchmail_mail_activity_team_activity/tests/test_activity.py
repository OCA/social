# © 2022 initOS GmbH
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import logging
import uuid

from odoo.fields import Command
from odoo.tests import TransactionCase

_logger = logging.getLogger(__name__)


class TestActivity(TransactionCase):
    def generate_reply(self, message):
        return (
            # "Date: Thu, 22 Sep 2022 12:23:20 +0000",
            "From: ext.partner@example.org\r\n"
            "To: odoo.test@local\r\n"
            f"Message-ID: {uuid.uuid4()}\r\n"
            f"In-Reply-To: {message['message_id']}\r\n"
            "Subject: Test Email Reply\r\n\r\n"
        )

    def test_no_team(self):
        thread = self.env.user.partner_id
        msg = thread.message_notify(
            partner_ids=self.env.user.partner_id.ids,
            body="Testing",
        )

        messages = thread.message_ids
        activities = thread.activity_ids
        reply = self.generate_reply(msg)

        thread_id = thread.message_process(thread._name, reply)
        self.assertTrue(len(messages) < len(thread.message_ids))
        self.assertEqual(activities, thread.activity_ids)
        self.assertEqual(thread_id, thread.id)

    def test_with_team(self):
        thread = self.env.user.partner_id
        model = self.env.ref("base.model_res_partner")

        self.env["mail.activity.team"].create(
            {
                "name": "Testing Team",
                "res_model_ids": [Command.set(model.ids)],
                "user_id": self.env.user.id,
            }
        )
        msg = thread.message_notify(
            partner_ids=self.env.user.partner_id.ids,
            body="Testing",
        )

        messages = thread.message_ids
        activities = thread.activity_ids
        reply = self.generate_reply(msg)

        thread_id = thread.message_process(thread._name, reply)
        self.assertTrue(len(messages) < len(thread.message_ids))
        self.assertEqual(thread_id, thread.id)

        activity = thread.activity_ids - activities
        self.assertTrue(activity)
        self.assertEqual(
            activity.activity_type_id,
            self.env.ref("mail.mail_activity_data_email"),
        )

        # Schedule it only once
        activities = thread.activity_ids
        reply = self.generate_reply(msg)
        thread.message_process(thread._name, reply)
        self.assertEqual(activities, thread.activity_ids)

    def test_with_team_no_activity_mixin(self):
        thread = self.env["calendar.event"].create({"name": "Testing"})
        model = self.env.ref("calendar.model_calendar_event")
        self.env["mail.activity.team"].create(
            {
                "name": "Testing Team",
                "res_model_ids": [Command.set(model.ids)],
                "user_id": self.env.user.id,
            }
        )
        msg = thread.message_notify(
            partner_ids=self.env.user.partner_id.ids,
            body="Testing",
        )

        activities = thread.activity_ids
        reply = self.generate_reply(msg)
        thread_id = thread.message_process(thread._name, reply)
        self.assertEqual(activities, thread.activity_ids)
        self.assertEqual(thread_id, thread.id)
