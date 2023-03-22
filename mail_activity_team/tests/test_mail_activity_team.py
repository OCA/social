# Copyright 2018 ForgeFlow, S.L.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from datetime import timedelta

from odoo.exceptions import ValidationError
from odoo.fields import Datetime
from odoo.tests.common import Form, SavepointCase


class TestMailActivityTeam(SavepointCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        self = cls
        self.env["mail.activity.team"].search([]).unlink()

        self.employee = self.env["res.users"].create(
            {
                "company_id": self.env.ref("base.main_company").id,
                "name": "Employee",
                "login": "csu",
                "email": "crmuser@yourcompany.com",
                "groups_id": [
                    (
                        6,
                        0,
                        [
                            self.env.ref("base.group_user").id,
                            self.env.ref("base.group_partner_manager").id,
                        ],
                    )
                ],
            }
        )

        self.employee2 = self.env["res.users"].create(
            {
                "company_id": self.env.ref("base.main_company").id,
                "name": "Employee 2",
                "login": "csu2",
                "email": "crmuser2@yourcompany.com",
                "groups_id": [(6, 0, [self.env.ref("base.group_user").id])],
            }
        )

        self.partner_ir_model = self.env["ir.model"]._get("res.partner")

        activity_type_model = self.env["mail.activity.type"]
        self.activity1 = activity_type_model.create(
            {
                "name": "Initial Contact",
                "delay_count": 5,
                "delay_unit": "days",
                "summary": "ACT 1 : Presentation, barbecue, ... ",
                "res_model_id": self.partner_ir_model.id,
            }
        )
        self.activity2 = activity_type_model.create(
            {
                "name": "Call for Demo",
                "delay_count": 6,
                "delay_unit": "days",
                "summary": "ACT 2 : I want to show you my ERP !",
                "res_model_id": self.partner_ir_model.id,
            }
        )

        self.partner_client = self.env.ref("base.res_partner_1")

        self.act1 = (
            self.env["mail.activity"]
            .with_user(self.employee)
            .create(
                {
                    "activity_type_id": self.activity1.id,
                    "note": "Partner activity 1.",
                    "res_id": self.partner_client.id,
                    "res_model_id": self.partner_ir_model.id,
                    "user_id": self.employee.id,
                }
            )
        )

        self.team1 = (
            self.env["mail.activity.team"]
            .sudo()
            .create(
                {
                    "name": "Team 1",
                    "res_model_ids": [(6, 0, [self.partner_ir_model.id])],
                    "member_ids": [(6, 0, [self.employee.id])],
                }
            )
        )

        self.team2 = (
            self.env["mail.activity.team"]
            .sudo()
            .create(
                {
                    "name": "Team 2",
                    "res_model_ids": [(6, 0, [self.partner_ir_model.id])],
                    "member_ids": [(6, 0, [self.employee.id, self.employee2.id])],
                }
            )
        )

        self.act2 = (
            self.env["mail.activity"]
            .with_user(self.employee)
            .create(
                {
                    "activity_type_id": self.activity2.id,
                    "note": "Partner activity 2.",
                    "res_id": self.partner_client.id,
                    "res_model_id": self.partner_ir_model.id,
                    "user_id": self.employee.id,
                }
            )
        )

        self.employee3 = self.env["res.users"].create(
            {
                "company_id": self.env.ref("base.main_company").id,
                "name": "Employee 3",
                "login": "csu3",
                "email": "crmuser3@yourcompany.com",
                "groups_id": [(6, 0, [self.env.ref("base.group_user").id])],
            }
        )

        self.act3 = (
            self.env["mail.activity"]
            .with_user(self.employee)
            .create(
                {
                    "activity_type_id": self.env.ref(
                        "mail.mail_activity_data_meeting"
                    ).id,
                    "note": "Meeting activity 3.",
                    "res_id": self.partner_client.id,
                    "res_model_id": self.partner_ir_model.id,
                    "user_id": self.employee.id,
                    "team_id": self.team1.id,
                    "summary": "Metting activity",
                }
            )
        )
        self.start = Datetime.now()
        self.stop = Datetime.to_string(
            Datetime.from_string(cls.start) + timedelta(hours=1)
        )

    def test_activity_members(self):
        self.team1.member_ids |= self.employee2
        self.partner_client.refresh()
        self.assertIn(self.employee2, self.partner_client.activity_team_user_ids)
        self.assertIn(self.employee, self.partner_client.activity_team_user_ids)
        self.assertEqual(
            self.partner_client,
            self.env["res.partner"].search(
                [("activity_team_user_ids", "=", self.employee.id)]
            ),
        )

    def test_team_and_user_onchange(self):
        with self.assertRaises(ValidationError):
            self.team1.member_ids = [(3, self.employee.id)]
            self.act2.team_id = self.team1
            self.act2.user_id = self.employee

    def test_missing_activities(self):
        self.assertFalse(self.act1.team_id, "Error: Activity 1 should not have a team.")
        self.assertEqual(self.team1.count_missing_activities, 1)
        self.team1.assign_team_to_unassigned_activities()
        self.team1._compute_missing_activities()
        self.assertEqual(self.team1.count_missing_activities, 0)
        self.assertEqual(self.act1.team_id, self.team1)

    def test_leader_onchange(self):
        self.team2.user_id = self.employee3
        self.team2._onchange_user_id()
        self.assertTrue(self.employee3 in self.team2.member_ids)

    def test_activity_onchanges_keep_user(self):
        self.assertEqual(
            self.act2.team_id, self.team1, "Error: Activity 2 should have Team 1."
        )
        with Form(self.act2) as form:
            form.team_id = self.env["mail.activity.team"]
            self.assertEqual(form.user_id, self.employee)

    def test_activity_onchanges_user_no_member_team(self):
        self.assertEqual(
            self.act2.team_id, self.team1, "Error: Activity 2 should have Team 1."
        )
        with Form(self.act2) as form:
            form.user_id = self.employee2
            self.assertEqual(form.team_id, self.team2)

    def test_activity_onchanges_user_no_team(self):
        self.assertEqual(
            self.act2.team_id, self.team1, "Error: Activity 2 should have Team 1."
        )
        with Form(self.act2) as form:
            form.team_id = self.env["mail.activity.team"]
            form.user_id = self.employee2
            self.assertEqual(form.team_id, self.team2)

    def test_activity_onchanges_team_no_member(self):
        self.assertEqual(
            self.act2.team_id, self.team1, "Error: Activity 2 should have Team 1."
        )
        self.team2.user_id = False
        self.team2.member_ids = False
        with Form(self.act2) as form:
            form.team_id = self.team2
            self.assertFalse(form.user_id)

    def test_activity_onchanges_team_different_member(self):
        self.assertEqual(
            self.act2.team_id, self.team1, "Error: Activity 2 should have Team 1."
        )
        self.team2.user_id = self.employee2
        self.team2.member_ids = self.employee2
        with Form(self.act2) as form:
            form.team_id = self.team2
            self.assertEqual(form.user_id, self.employee2)

    def test_activity_onchanges_team_different_member_no_leader(self):
        self.assertEqual(
            self.act2.team_id, self.team1, "Error: Activity 2 should have Team 1."
        )
        self.team2.user_id = False
        self.team2.member_ids = self.employee2
        with Form(self.act2) as form:
            form.team_id = self.team2
            self.assertEqual(form.user_id, self.employee2)

    def test_activity_onchanges_activity_type_set_team(self):
        self.assertEqual(
            self.act2.team_id, self.team1, "Error: Activity 2 should have Team 1."
        )
        self.activity1.default_team_id = self.team2
        self.assertEqual(self.act2.activity_type_id, self.activity2)
        with Form(self.act2) as form:
            form.activity_type_id = self.activity1
            self.assertEqual(form.team_id, self.team2)

    def test_activity_onchanges_activity_type_no_team(self):
        self.assertEqual(
            self.act2.team_id, self.team1, "Error: Activity 2 should have Team 1."
        )
        self.assertEqual(self.act2.activity_type_id, self.activity2)
        with Form(self.act2) as form:
            form.activity_type_id = self.activity1
            self.assertEqual(form.team_id, self.team1)

    def test_activity_constrain(self):
        with self.assertRaises(ValidationError):
            self.act2.write({"user_id": self.employee2.id, "team_id": self.team1.id})

    def test_schedule_activity(self):
        """Correctly assign teams to auto scheduled activities. Those won't
        trigger onchanges and could raise constraints and team missmatches"""
        partner_record = self.employee.partner_id.with_user(self.employee.id)
        activity = partner_record.activity_schedule(
            user_id=self.employee2.id,
            activity_type_id=self.env.ref("mail.mail_activity_data_call").id,
        )
        self.assertEqual(activity.team_id, self.team2)

    def test_schedule_activity_default_team(self):
        """Correctly assign teams to auto scheduled activities. Those won't
        trigger onchanges and could raise constraints and team missmatches"""
        partner_record = self.employee.partner_id.with_user(self.employee.id)
        self.env.ref("mail.mail_activity_data_call").default_team_id = self.team2
        activity = partner_record.activity_schedule(
            act_type_xmlid="mail.mail_activity_data_call",
            user_id=self.employee2.id,
        )
        self.assertEqual(activity.team_id, self.team2)
        self.assertEqual(activity.user_id, self.employee2)

    def test_schedule_activity_default_team_no_user(self):
        """Correctly assign teams to auto scheduled activities. Those won't
        trigger onchanges and could raise constraints and team missmatches"""
        partner_record = self.employee.partner_id.with_user(self.employee.id)
        self.activity2.default_team_id = self.team2
        self.team2.member_ids = self.employee2
        activity = partner_record.activity_schedule(
            activity_type_id=self.activity2.id,
        )
        self.assertEqual(activity.team_id, self.team2)
        self.assertEqual(activity.user_id, self.employee2)

    def test_activity_count(self):
        res = (
            self.env["res.users"]
            .with_user(self.employee.id)
            .with_context({"team_activities": True})
            .systray_get_activities()
        )
        self.assertEqual(res[0]["total_count"], 0)
        self.assertEqual(res[0]["today_count"], 2)
        partner_record = self.employee.partner_id.with_user(self.employee.id)
        self.activity2.default_team_id = self.team2
        activity = partner_record.activity_schedule(
            activity_type_id=self.activity2.id, user_id=self.employee2.id
        )
        activity.flush()
        res = (
            self.env["res.users"]
            .with_user(self.employee.id)
            .with_context({"team_activities": True})
            .systray_get_activities()
        )
        self.assertEqual(res[0]["total_count"], 1)
        self.assertEqual(res[0]["today_count"], 3)
        res = self.env["res.users"].with_user(self.employee.id).systray_get_activities()
        self.assertEqual(res[0]["total_count"], 3)

    def test_activity_schedule_next(self):
        self.activity1.write(
            {
                "default_team_id": self.team1.id,
                "default_next_type_id": self.activity2.id,
                "force_next": True,
            }
        )
        self.activity2.default_team_id = self.team2
        self.team2.member_ids = self.employee2
        partner_record = self.employee.partner_id.with_user(self.employee.id)
        activity = partner_record.activity_schedule(activity_type_id=self.activity1.id)
        activity.flush()
        _messages, next_activities = activity._action_done()
        self.assertTrue(next_activities)
        self.assertEqual(next_activities.team_id, self.team2)
        self.assertEqual(next_activities.user_id, self.employee2)

    def test_meeting_blank(self):
        meeting = (
            self.env["calendar.event"]
            .with_user(self.employee)
            .create({"start": self.start, "stop": self.stop, "name": "Test meeting"})
        )
        self.assertTrue(meeting.team_id)

    def test_meeting_from_activity(self):
        action = self.act3.with_context(
            default_res_id=self.act3.res_id,
            default_res_model=self.act3.res_model,
        ).action_create_calendar_event()

        meeting = (
            self.env["calendar.event"]
            .with_user(self.employee)
            .with_context(**action["context"])
            .create({"start": self.start, "stop": self.stop})
        )
        self.assertTrue(meeting.team_id)
        self.assertTrue(meeting.read(["description"])[0]["description"])
        self.assertTrue(
            meeting.with_user(self.employee2).read(["description"])[0]["description"],
            "He should be able to read the record as it is public by default",
        )
        meeting.write({"privacy": "team"})
        self.assertFalse(
            meeting.with_user(self.employee2).read(["description"])[0]["description"],
            "He shouldn't be able to read the record as it is private",
        )
