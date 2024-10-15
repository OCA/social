# Copyright 2024 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl)

from odoo import fields
from odoo.tests.common import TransactionCase


class TestNotificationErrorCleanUp(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))
        cls.partner = cls.env.ref("base.res_partner_address_28")
        cls.message = cls.env["mail.message"].create(
            {
                "model": "res.partner",
                "res_id": cls.partner.id,
                "body": "TEST",
                "message_type": "email",
                "subtype_id": cls.env.ref("mail.mt_comment").id,
                "author_id": cls.partner.id,
                "date": "2024-03-26",
            }
        )
        cls.notification = cls.env["mail.notification"].create(
            {
                "mail_message_id": cls.message.id,
                "res_partner_id": cls.partner.id,
                "notification_type": "email",
                "notification_status": "bounce",
            }
        )

    def test_notification_in_error_not_read(self):
        # While the notification is not read, it is not deleted
        self.env["mail.notification"]._gc_notifications(max_age_days=1)
        self.assertTrue(self.notification.exists())
        # Once the notification is read, the GC will delete it
        # NOTE: update the read data in two steps as 'read_date' is overwritten
        # when 'is_read' is set.
        read_date = fields.Datetime.subtract(fields.Datetime.now(), days=2)
        self.notification.is_read = True
        self.notification.read_date = read_date
        self.env["mail.notification"]._gc_notifications(max_age_days=1)
        self.assertFalse(self.notification.exists())
