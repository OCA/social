# Copyright 2023 Hunki Enterprises BV
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from odoo.exceptions import AccessError, UserError
from odoo.tests.common import TransactionCase
from odoo.tools import mute_logger


class TestMailActivityPermission(TransactionCase):
    def setUp(self):
        super().setUp()
        self.user = self.env.ref("base.user_demo")
        self.company = self.env["res.company"].create({"name": "Another company"})
        self.partner = self.company.partner_id
        self.partner.company_id = self.company
        self.activity_type = self.env["mail.activity.type"].create(
            {
                "res_model_id": self.env.ref("base.model_res_partner").id,
                "name": "Do something with the partner",
                "perm_read": True,
                "perm_write": True,
            }
        )

    def test_access(self):
        """
        Test basic functionality
        """
        with self.assertRaises(AccessError), mute_logger(
            "odoo.addons.base.models.ir_rule"
        ):
            self.company.partner_id.with_user(self.user).read()
        self.env["mail.activity.bulk.assign"].with_context(
            active_model=self.partner._name,
            active_id=self.partner.id,
            active_ids=self.partner.ids,
        ).create(
            {
                "activity_type_id": self.activity_type.id,
                "user_ids": [(6, False, self.user.ids)],
            }
        )
        self.assertEqual(
            self.company.partner_id.with_user(self.user).read(["name"]),
            self.company.partner_id.read(["name"]),
        )
        child = self.env["res.partner"].create(
            {
                "parent_id": self.partner.id,
                "name": "Child, should be inaccessible",
                "company_id": self.company.id,
            }
        )
        with self.assertRaises(AccessError), mute_logger(
            "odoo.addons.base.models.ir_rule"
        ):
            child.with_user(self.user).read()
        self.activity_type.field_ids = self.env.ref(
            "base.field_res_partner__child_ids"
        ) + self.env.ref("base.field_res_partner__bank_ids")
        self.assertEqual(
            child.with_user(self.user).read(["name"]), child.read(["name"]),
        )

    def test_code(self):
        """
        Test that adding code to activity types works
        """
        self.activity_type.write(
            {
                "name": "Deactivate the partner",
                "code_activity_done": "record.sudo().write({'active': False})",
                "code_user_selection": "env['res.users'].browse(%s)" % self.user.id,
            }
        )
        self.env["mail.activity.bulk.assign"].with_context(
            active_model=self.partner._name,
            active_id=self.partner.id,
            active_ids=self.partner.ids,
        ).create({"activity_type_id": self.activity_type.id})
        activity = self.partner.activity_ids
        self.assertEqual(len(activity), 1)
        self.assertEqual(activity.user_id, self.user)
        activity.with_user(self.user).action_done()
        self.assertFalse(self.partner.active)

    def test_action_binding(self):
        """
        Test we only show the bulk assign wizard for models with activities
        """
        action = self.env.ref(
            "mail_activity_permission.action_mail_activity_bulk_assign"
        ).read()[0]
        partner_bindings = self.env["ir.actions.actions"].get_bindings("res.partner")
        self.assertIn(action, partner_bindings["action"])
        group_bindings = self.env["ir.actions.actions"].get_bindings("res.groups")
        self.assertNotIn(action, group_bindings["action"])

    def test_misc(self):
        """
        Test misc functions
        """
        with self.assertRaises(UserError):
            self.activity_type.write({"code_activity_done": "wrong(code"})
