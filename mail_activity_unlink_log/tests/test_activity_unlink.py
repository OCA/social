# Copyright 2023 CreuBlanca
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo.tests.common import TransactionCase


class TestActivityUnlink(TransactionCase):
    def setUp(self):
        super().setUp()
        self.partner = self.env["res.partner"].create({"name": "Partner"})
        self.unlink_subtype = self.env.ref(
            "mail_activity_unlink_log.mt_activities_unlink"
        )

    def test_done(self):
        self.assertFalse(
            self.partner.message_ids.filtered(
                lambda r: r.subtype_id == self.unlink_subtype
            )
        )
        self.activity = self.partner.activity_schedule(
            act_type_xmlid="mail.mail_activity_data_todo"
        )
        self.assertTrue(self.partner.activity_ids)
        self.activity.action_done()
        self.assertFalse(self.partner.activity_ids)
        self.assertFalse(
            self.partner.message_ids.filtered(
                lambda r: r.subtype_id == self.unlink_subtype
            )
        )

    def test_unlink(self):
        self.assertFalse(
            self.partner.message_ids.filtered(
                lambda r: r.subtype_id == self.unlink_subtype
            )
        )
        self.activity = self.partner.activity_schedule(
            act_type_xmlid="mail.mail_activity_data_todo"
        )
        self.assertTrue(self.partner.activity_ids)
        self.activity.unlink()
        self.assertFalse(self.partner.activity_ids)
        self.assertTrue(
            self.partner.message_ids.filtered(
                lambda r: r.subtype_id == self.unlink_subtype
            )
        )
