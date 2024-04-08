# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from datetime import date

from odoo.tests.common import TransactionCase


class TestMailActivityDoneMethods(TransactionCase):
    def setUp(self):
        super().setUp()

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
                "res_model": "res.partner",
                "res_model_id": self.env["ir.model"]._get("res.partner").id,
                "user_id": self.employee.id,
                "date_deadline": date.today(),
            }
        )

    def test_mail_activity_done(self):
        self.act1._action_done()
        self.assertTrue(self.act1.exists())
        self.assertEqual(self.act1.state, "done")

    def test_systray_get_activities(self):
        act_count = self.employee.with_user(self.employee).systray_get_activities()
        self.assertEqual(
            len(act_count), 1, "Number of activities should be equal to one"
        )

    def test_mail_activity_search(self):
        # Cover `_search_state` for mail.activity
        self.act1._action_done()
        self.assertEqual(
            self.env["mail.activity"].search_count(
                [("state", "=", "done"), ("active", "=", False)]
            ),
            1,
        )
        self.assertEqual(
            self.env["mail.activity"].search_count(
                [("state", "!=", "done"), ("active", "=", False)]
            ),
            0,
        )
        self.assertEqual(
            self.env["mail.activity"].search_count(
                [("state", "!=", "today"), ("active", "=", False)]
            ),
            1,
        )
        self.assertFalse(
            self.env["mail.activity"].search_count(
                [("state", "=", "today"), ("active", "=", False)]
            )
        )
        self.assertFalse(self.env["mail.activity"].search([("state", "=", False)]))
        self.env["mail.activity"].search([("state", "!=", False)])
