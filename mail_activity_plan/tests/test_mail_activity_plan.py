# Copyright 2024 Tecnativa - Víctor Martínez
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo.exceptions import UserError
from odoo.tests import Form, new_test_user
from odoo.tests.common import users

from odoo.addons.base.tests.common import BaseCommon


class TestMailActivityPlan(BaseCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user_plan = new_test_user(
            cls.env,
            login="test_user_plan",
            groups="base.group_user,base.group_partner_manager",
        )
        cls.user_extra = new_test_user(cls.env, login="test_user_extra")
        cls.user_admin = cls.env.ref("base.user_admin")
        cls.user_demo = cls.env.ref("base.user_demo")
        cls.group_1 = cls.env["res.groups"].create(
            {
                "name": "Test group 1",
                "users": [(4, cls.user_plan.id)],
            }
        )
        cls.group_2 = cls.env["res.groups"].create(
            {
                "name": "Test group 2",
                "users": [(4, cls.user_plan.id)],
            }
        )
        cls.plan_1 = cls.env.ref("mail_activity_plan.mail_activity_plan_demo_1")
        cls.plan_1.group_ids = [(6, 0, cls.group_1.ids)]
        cls.plan_2 = cls.env.ref("mail_activity_plan.mail_activity_plan_demo_2")
        cls.plan_2.group_ids = [(6, 0, cls.group_2.ids)]
        cls.partner = cls.env["res.partner"].create(
            {"name": "Test partner", "user_id": cls.user_extra.id}
        )
        cls.partner_extra = cls.env["res.partner"].create(
            {"name": "Test partner extra", "user_id": cls.user_extra.id}
        )
        cls.activity_type_email = cls.env.ref("mail.mail_activity_data_email")
        cls.activity_type_call = cls.env.ref("mail.mail_activity_data_call")
        cls.activity_type_todo = cls.env.ref("mail.mail_activity_data_todo")

    def _action_wizard_mail_activity_plan(self, records):
        action = self.env["ir.actions.act_window"]._for_xml_id(
            "mail_activity_plan.action_wizard_mail_activity_plan"
        )
        ctx = dict(
            self.env.context,
            active_ids=records.ids,
            default_res_model=records._name,
        )
        return self.env[action["res_model"]].with_context(**ctx).create({})

    @users("test_user_extra")
    def test_wizard_mail_activity_plan_0(self):
        self.partner = self.partner.with_user(self.env.user)
        wizard = self._action_wizard_mail_activity_plan(self.partner)
        self.assertFalse(wizard.allowed_activity_plans)
        # Add user to group 1
        self.user_extra.groups_id = [(4, self.group_1.id)]
        wizard._compute_allowed_activity_plans()
        self.assertIn(self.plan_1, wizard.allowed_activity_plans)
        self.assertNotIn(self.plan_2, wizard.allowed_activity_plans)
        # Add user to group 2
        self.user_extra.groups_id = [(4, self.group_2.id)]
        wizard._compute_allowed_activity_plans()
        self.assertIn(self.plan_1, wizard.allowed_activity_plans)
        self.assertIn(self.plan_2, wizard.allowed_activity_plans)

    @users("test_user_plan")
    def test_wizard_mail_activity_plan_1(self):
        self.partner = self.partner.with_user(self.env.user)
        wizard = self._action_wizard_mail_activity_plan(self.partner)
        self.assertIn(self.plan_1, wizard.allowed_activity_plans)
        self.assertIn(self.plan_2, wizard.allowed_activity_plans)
        self.assertFalse(wizard.detail_ids)
        wizard_form = Form(wizard)
        wizard_form.activity_plan_id = self.plan_1
        wizard_form.save()
        self.assertEqual(len(wizard.detail_ids), 3)
        self.assertNotIn("Satisfaction survey", wizard.mapped("detail_ids.summary"))
        detail_1 = wizard.detail_ids.filtered(lambda x: x.summary == "Wellcome mail")
        self.assertEqual(detail_1.activity_type_id, self.activity_type_email)
        self.assertEqual(detail_1.user_id, self.user_admin)
        detail_2 = wizard.detail_ids.filtered(lambda x: x.summary == "First call")
        self.assertEqual(detail_2.activity_type_id, self.activity_type_call)
        self.assertEqual(detail_2.user_id, self.user_admin)
        detail_3 = wizard.detail_ids.filtered(lambda x: x.summary == "Send a quotation")
        self.assertEqual(detail_3.activity_type_id, self.activity_type_todo)
        self.assertEqual(detail_3.user_id, self.user_demo)
        # action_launch to create activities
        activities = wizard.action_launch()
        self.assertEqual(len(activities), 3)
        activity_1 = activities.filtered(lambda x: x.summary == "Wellcome mail")
        self.assertEqual(activity_1.activity_type_id, self.activity_type_email)
        self.assertEqual(activity_1.user_id, self.user_admin)
        activity_2 = activities.filtered(lambda x: x.summary == "First call")
        self.assertEqual(activity_2.activity_type_id, self.activity_type_call)
        self.assertEqual(activity_2.user_id, self.user_admin)
        activity_3 = activities.filtered(lambda x: x.summary == "Send a quotation")
        self.assertEqual(activity_3.activity_type_id, self.activity_type_todo)
        self.assertEqual(activity_3.user_id, self.user_demo)
        self.assertNotIn("Satisfaction survey", activities.mapped("summary"))

    @users("test_user_plan")
    def test_wizard_mail_activity_plan_2(self):
        self.partner = self.partner.with_user(self.env.user)
        wizard = self._action_wizard_mail_activity_plan(self.partner)
        self.assertIn(self.plan_1, wizard.allowed_activity_plans)
        self.assertIn(self.plan_2, wizard.allowed_activity_plans)
        self.assertFalse(wizard.detail_ids)
        wizard_form = Form(wizard)
        wizard_form.activity_plan_id = self.plan_2
        wizard_form.save()
        self.assertEqual(len(wizard.detail_ids), 4)
        detail_1 = wizard.detail_ids.filtered(lambda x: x.summary == "Wellcome mail")
        self.assertEqual(detail_1.activity_type_id, self.activity_type_email)
        self.assertEqual(detail_1.user_id, self.user_admin)
        detail_2 = wizard.detail_ids.filtered(lambda x: x.summary == "First call")
        self.assertEqual(detail_2.activity_type_id, self.activity_type_call)
        self.assertEqual(detail_2.user_id, self.user_admin)
        detail_3 = wizard.detail_ids.filtered(lambda x: x.summary == "Send a quotation")
        self.assertEqual(detail_3.activity_type_id, self.activity_type_todo)
        self.assertEqual(detail_3.user_id, self.user_demo)
        detail_4 = wizard.detail_ids.filtered(
            lambda x: x.summary == "Satisfaction survey"
        )
        self.assertEqual(detail_4.activity_type_id, self.activity_type_todo)
        self.assertEqual(detail_4.user_id, self.user_extra)
        # action_launch to create activities
        activities = wizard.action_launch()
        self.assertEqual(len(activities), 4)
        activity_1 = activities.filtered(lambda x: x.summary == "Wellcome mail")
        self.assertEqual(activity_1.activity_type_id, self.activity_type_email)
        self.assertEqual(activity_1.user_id, self.user_admin)
        activity_2 = activities.filtered(lambda x: x.summary == "First call")
        self.assertEqual(activity_2.activity_type_id, self.activity_type_call)
        self.assertEqual(activity_2.user_id, self.user_admin)
        activity_3 = activities.filtered(lambda x: x.summary == "Send a quotation")
        self.assertEqual(activity_3.activity_type_id, self.activity_type_todo)
        self.assertEqual(activity_3.user_id, self.user_demo)
        activity_4 = activities.filtered(lambda x: x.summary == "Satisfaction survey")
        self.assertEqual(activity_4.activity_type_id, self.activity_type_todo)
        self.assertEqual(activity_4.user_id, self.user_extra)

    @users("test_user_plan")
    def test_wizard_mail_activity_plan_3(self):
        self.partner = self.partner.with_user(self.env.user)
        self.partner.user_id = False
        wizard = self._action_wizard_mail_activity_plan(self.partner)
        wizard_form = Form(wizard)
        with self.assertRaises(UserError):
            wizard_form.activity_plan_id = self.plan_2

    @users("test_user_plan")
    def test_wizard_mail_activity_plan_4(self):
        partners = self.partner + self.partner_extra
        wizard = self._action_wizard_mail_activity_plan(partners)
        wizard_form = Form(wizard)
        wizard_form.activity_plan_id = self.plan_1
        wizard_form.save()
        self.assertEqual(len(wizard.detail_ids), 6)
        activities = wizard.action_launch()
        # activities_partner
        activities_partner = activities.filtered(
            lambda x: x.res_model == self.partner._name and x.res_id == self.partner.id
        )
        self.assertEqual(len(activities_partner), 3)
        activity_1 = activities_partner.filtered(lambda x: x.summary == "Wellcome mail")
        self.assertEqual(activity_1.activity_type_id, self.activity_type_email)
        self.assertEqual(activity_1.user_id, self.user_admin)
        activity_2 = activities_partner.filtered(lambda x: x.summary == "First call")
        self.assertEqual(activity_2.activity_type_id, self.activity_type_call)
        self.assertEqual(activity_2.user_id, self.user_admin)
        activity_3 = activities_partner.filtered(
            lambda x: x.summary == "Send a quotation"
        )
        self.assertEqual(activity_3.activity_type_id, self.activity_type_todo)
        self.assertEqual(activity_3.user_id, self.user_demo)
        self.assertNotIn("Satisfaction survey", activities_partner.mapped("summary"))
        # activities_partner_extra
        activities_partner_extra = activities.filtered(
            lambda x: x.res_model == self.partner_extra._name
            and x.res_id == self.partner_extra.id
        )
        self.assertEqual(len(activities_partner_extra), 3)
        activity_1 = activities_partner_extra.filtered(
            lambda x: x.summary == "Wellcome mail"
        )
        self.assertEqual(activity_1.activity_type_id, self.activity_type_email)
        self.assertEqual(activity_1.user_id, self.user_admin)
        activity_2 = activities_partner_extra.filtered(
            lambda x: x.summary == "First call"
        )
        self.assertEqual(activity_2.activity_type_id, self.activity_type_call)
        self.assertEqual(activity_2.user_id, self.user_admin)
        activity_3 = activities_partner_extra.filtered(
            lambda x: x.summary == "Send a quotation"
        )
        self.assertEqual(activity_3.activity_type_id, self.activity_type_todo)
        self.assertEqual(activity_3.user_id, self.user_demo)
        self.assertNotIn(
            "Satisfaction survey", activities_partner_extra.mapped("summary")
        )
