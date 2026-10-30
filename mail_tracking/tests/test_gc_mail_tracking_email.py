# Copyright 2024 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl)

from odoo import fields

from odoo.addons.base.tests.common import SavepointCaseWithUserDemo


class TestMailTrackingEmailCleanUp(SavepointCaseWithUserDemo):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))
        cls.settings = cls.env["res.config.settings"].create(
            {"mail_tracking_email_max_age_days": 365}
        )
        cls.settings.set_values()
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
        cls.recent_mail_tracking_email = cls.env["mail.tracking.email"].create(
            {"mail_message_id": cls.message.id}
        )
        # Can't set the write_date directly as it gets overwritten by the ORM
        cls.old_mail_tracking_email = cls.env["mail.tracking.email"].create(
            {"mail_message_id": cls.message.id}
        )
        cls.total_count = 2
        cls.recent_count = 1
        cls.domain = [
            ("mail_message_id", "=", cls.message.id),
        ]

    def _set_write_date(self):
        # Set the write_date of the old record to be older than the max_age_days
        # Update DB directly to avoid ORM overwriting the write_date
        old_write_date = fields.Datetime.subtract(fields.Datetime.now(), days=400)
        self.env.cr.execute(
            "UPDATE mail_tracking_email SET write_date = %s WHERE id = %s",
            (old_write_date, self.old_mail_tracking_email.id),
        )

    def test_deletion_of_mail_tracking_email(self):
        self._set_write_date()
        self.assertEqual(
            len(self.env["mail.tracking.email"].search(self.domain)), self.total_count
        )
        self.env["mail.tracking.email"]._gc_mail_tracking_email()
        self.assertEqual(
            len(self.env["mail.tracking.email"].search(self.domain)), self.recent_count
        )
        self.assertTrue(self.recent_mail_tracking_email.exists())

    def test_deletion_follows_configuration_variable(self):
        self._set_write_date()
        self.assertEqual(
            len(self.env["mail.tracking.email"].search(self.domain)), self.total_count
        )
        # when disabled, no deletions should happen
        self.settings.mail_tracking_email_max_age_days = 0
        self.settings.set_values()
        self.env["mail.tracking.email"]._gc_mail_tracking_email()
        self.assertEqual(
            len(self.env["mail.tracking.email"].search(self.domain)), self.total_count
        )
        # when disabled, no deletions should happen
        self.settings.mail_tracking_email_max_age_days = -1
        self.settings.set_values()
        self.env["mail.tracking.email"]._gc_mail_tracking_email()
        self.assertEqual(
            len(self.env["mail.tracking.email"].search(self.domain)), self.total_count
        )
        # when enabled, deletions should happen
        self.settings.mail_tracking_email_max_age_days = 365
        self.settings.set_values()
        self.env["mail.tracking.email"]._gc_mail_tracking_email()
        self.assertEqual(
            len(self.env["mail.tracking.email"].search(self.domain)), self.recent_count
        )
