# Copyright 2018 David Juaneda - <djuaneda@sdi.es>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
from odoo import Command

from odoo.addons.base.tests.common import BaseCommon


class TestMailActivityBoardMethods(BaseCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Set up activities

        # Create a user with the basic internal user group
        mail_activity_group = cls.create_mail_activity_group()
        cls.employee = cls.env["res.users"].create(
            {
                "company_id": cls.env.ref("base.main_company").id,
                "name": "Employee",
                "login": "csu",
                "email": "crmuser@yourcompany.com",
                "group_ids": [Command.set([cls.env.ref("base.group_user").id])],
            }
        )

        # Create a user who doesn't have access to anything except activities
        cls.employee2 = cls.env["res.users"].create(
            {
                "company_id": cls.env.ref("base.main_company").id,
                "name": "Employee2",
                "login": "alien",
                "email": "alien@yourcompany.com",
                "group_ids": [Command.set([mail_activity_group.id])],
            }
        )

        partner_model = cls.env["ir.model"]._get("res.partner")

        ActivityType = cls.env["mail.activity.type"]
        cls.activity1 = ActivityType.create(
            {
                "name": "Initial Contact",
                "delay_count": 5,
                "delay_unit": "days",
                "summary": "ACT 1 : Presentation, barbecue, ... ",
                "res_model": partner_model.model,
            }
        )
        cls.activity2 = ActivityType.create(
            {
                "name": "Call for Demo",
                "delay_count": 6,
                "delay_unit": "days",
                "summary": "ACT 2 : I want to show you my ERP !",
                "res_model": partner_model.model,
            }
        )
        cls.activity3 = ActivityType.create(
            {
                "name": "Celebrate the sale",
                "delay_count": 3,
                "delay_unit": "days",
                "summary": "ACT 3 : Beers for everyone because I am a good salesman !",
                "res_model": partner_model.model,
            }
        )

        cls.partner_client = cls.env["res.partner"].create({"name": "Test Client"})

        # assure there isn't any mail activity yet
        cls.env["mail.activity"].sudo().search([]).unlink()

        Activity = cls.env["mail.activity"].sudo()
        cls.act1 = Activity.create(
            {
                "activity_type_id": cls.activity3.id,
                "note": "Partner activity 1.",
                "res_id": cls.partner_client.id,
                "res_model_id": partner_model.id,
                "user_id": cls.employee.id,
            }
        )
        cls.act2 = Activity.create(
            {
                "activity_type_id": cls.activity2.id,
                "note": "Partner activity 2.",
                "res_id": cls.partner_client.id,
                "res_model_id": partner_model.id,
                "user_id": cls.employee.id,
            }
        )
        cls.act3 = Activity.create(
            {
                "activity_type_id": cls.activity3.id,
                "note": "Partner activity 3.",
                "res_id": cls.partner_client.id,
                "res_model_id": partner_model.id,
                "user_id": cls.employee.id,
            }
        )

    @classmethod
    def create_mail_activity_group(cls):
        manager_mail_activity_test_group = cls.env["res.groups"].create(
            {"name": "group_manager_mail_activity_test"}
        )
        mail_activity_model = cls.env["ir.model"].sudo()._get("mail.activity")
        cls.env["ir.model.access"].create(
            {
                "name": "full_access_mail_activity",
                "model_id": mail_activity_model.id,
                "group_id": manager_mail_activity_test_group.id,
                "perm_read": True,
                "perm_write": True,
                "perm_create": True,
                "perm_unlink": True,
            }
        )
        return manager_mail_activity_test_group

    def get_view(self, activity):
        action = activity.open_origin()
        result = self.env[action.get("res_model")].get_views(action.get("views"))
        return result.get("views").get(action.get("view_mode"))

    def test_open_origin_res_partner(self):
        """This test case checks
        - If the method redirects to the form view of the correct one
        of an object of the 'res.partner' class to which the activity
        belongs.
        """
        form_view_partner_id = self.env.ref("base.view_partner_form").id
        for activity in (self.act1, self.act2, self.act3):
            view = self.get_view(activity)
            self.assertEqual(form_view_partner_id, view.get("id"))

    def test_redirect_to_activities(self):
        """This test case checks
        - if the method returns the correct action,
        - if the correct activities are shown.
        """
        action_id = self.env.ref("mail_activity_board.open_boards_activities").id
        action = self.partner_client.redirect_to_activities(
            id=self.partner_client.id,
            model=self.partner_client._name,
        )
        self.assertEqual(action.get("id"), action_id)
        self.assertIn("list", [view_type for _view_id, view_type in action["views"]])

        Activity = self.env["mail.activity"]
        groups = Activity.formatted_read_group(
            domain=action.get("domain"), groupby=["activity_type_id"]
        )
        acts = Activity.browse()
        for group in groups:
            acts |= Activity.search(group["__extra_domain"] + action.get("domain"))
        self.assertEqual(acts, self.partner_client.activity_ids)

    def test_related_model_instance(self):
        """This test case checks the direct access from the activity to the
        linked model instance
        """
        self.assertEqual(self.act3.related_model_instance, self.partner_client)
        self.act3.write({"res_id": False, "res_model": False})
        self.assertFalse(self.act3.related_model_instance)
