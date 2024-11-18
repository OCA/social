# Copyright 2024 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

import datetime

from dateutil.relativedelta import relativedelta
from freezegun import freeze_time

from odoo.tests import SavepointCase


class TestMailMessagePurge(SavepointCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))
        cls.customer = cls.env["res.partner"].create({"name": "Customer One"})
        # Use the partner model to test
        cls.contact = cls.env["res.partner"].create({"name": "Contact One"})
        cls.mt_comment = cls.env.ref("mail.mt_comment")
        cls.mt_note = cls.env.ref("mail.mt_note")
        cls.mm1 = cls.contact.message_post(body="Hello", subtype_id=cls.mt_note.id)
        cls.mm2 = cls.contact.message_notify(
            partner_ids=cls.customer.ids, body="Hello Two"
        )
        contact_model = cls.env.ref("base.model_res_partner")
        cls.mm_purge = cls.env["mail.message.purge"].create(
            {
                "res_model": contact_model.id,
                "domain": f"[('id', '=', {cls.contact.id})]",
                "retention_period": 1,
            }
        )

    def test_purge_before_retention_period(self):
        """Check message is not deleted during retention period."""
        purge_time = datetime.datetime.now() + relativedelta(days=360)
        with freeze_time(purge_time):
            self.env["mail.message.purge"]._cron_purge_mail_message()
        self.assertTrue(self.mm1.exists())
        self.assertTrue(self.mm2.exists())

    def test_purge_after_retention_period(self):
        """Check message is deleted after the retention period."""
        purge_time = datetime.datetime.now() + relativedelta(days=370)
        with freeze_time(purge_time):
            self.env["mail.message.purge"]._cron_purge_mail_message()
        self.assertFalse(self.mm1.exists())
        self.assertTrue(self.mm2.exists())
        # Check including the user notification message type
        self.mm_purge.include_user_notification = True
        with freeze_time(purge_time):
            self.env["mail.message.purge"]._cron_purge_mail_message()
        self.assertFalse(self.mm2.exists())

    def test_purge_in_relation_to_subtype(self):
        """Check deletion or not of messages based on subtype."""
        purge_time = datetime.datetime.now() + relativedelta(days=370)
        # Message is of type note, configure purge to delete comment subtype
        self.mm_purge.mail_message_subtype_ids = [(6, 0, self.mt_comment.ids)]
        with freeze_time(purge_time):
            self.env["mail.message.purge"]._cron_purge_mail_message()
        # Message not deleted
        self.assertTrue(self.mm1.exists())
        # Configure to purge message of subtype note
        self.mm_purge.mail_message_subtype_ids = [(6, 0, self.mt_note.ids)]
        with freeze_time(purge_time):
            self.env["mail.message.purge"]._cron_purge_mail_message()
        self.assertFalse(self.mm1.exists())
