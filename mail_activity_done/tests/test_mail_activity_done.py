# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
# Copyright 2023 Tecnativa - Víctor Martínez
from datetime import date

from odoo.tests.common import TransactionCase, new_test_user


class TestMailActivityDoneMethods(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(
            context=dict(
                cls.env.context,
                mail_activity_quick_update=True,
                mail_create_nolog=True,
                mail_create_nosubscribe=True,
                mail_notrack=True,
                no_reset_password=True,
                tracking_disable=True,
            )
        )
        cls.employee = new_test_user(
            cls.env,
            name="Test User",
            login="testuser",
        )
        activity_type = cls.env["mail.activity.type"].search(
            [("name", "=", "Meeting")], limit=1
        )
        cls.act1 = cls.env["mail.activity"].create(
            {
                "activity_type_id": activity_type.id,
                "res_id": cls.env.ref("base.res_partner_1").id,
                "res_model_id": cls.env["ir.model"]._get("res.partner").id,
                "user_id": cls.employee.id,
                "date_deadline": date.today(),
            }
        )

    def test_mail_activity_done(self):
        self.act1.done = True
        self.assertEqual(self.act1.state, "done")

    def test_systray_get_activities(self):
        res = self.employee.with_user(self.employee).systray_get_activities()
        self.assertEqual(res[0]["total_count"], 1)
        self.act1.action_feedback()
        self.assertFalse(self.act1.active)
        self.assertEqual(self.act1.state, "done")
        self.assertTrue(self.act1.done)
        self.act1.flush()
        res = self.employee.with_user(self.employee).systray_get_activities()
        self.assertEqual(res[0]["total_count"], 0)
