# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
# Copyright 2023 Tecnativa - Víctor Martínez
from datetime import date

from odoo.tests.common import TransactionCase


class TestMailActivityDoneMethods(TransactionCase):
    def setUp(self):
        super(TestMailActivityDoneMethods, self).setUp()

        self.employee = self.env["res.users"].create(
            {
                "company_id": self.env.ref("base.main_company").id,
                "name": "Test User",
                "login": "testuser",
                "groups_id": [(6, 0, [self.env.ref("base.group_user").id])],
            }
        )
        activity_type = self.env["mail.activity.type"].search(
            [("name", "=", "Meeting")], limit=1
        )
        self.act1 = self.env["mail.activity"].create(
            {
                "activity_type_id": activity_type.id,
                "res_id": self.env.ref("base.res_partner_1").id,
                "res_model_id": self.env["ir.model"]._get("res.partner").id,
                "user_id": self.employee.id,
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
