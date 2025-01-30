# Copyright 2023 Ooops404
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
from odoo.tests.common import TransactionCase


class TestMailActivityReplyCreator(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))
        cls.user_model = cls.env["res.users"].with_context(no_reset_password=True)
        cls.user_admin = cls.env.ref("base.user_root")
        cls.user_2 = cls.env["res.users"].search([])[-1]
        cls.partner_ir_model = cls.env["ir.model"]._get("res.partner")
        cls.partner_01 = cls.env.ref("base.res_partner_1")
        activity_type_model = cls.env["mail.activity.type"]
        cls.activity_type_1 = activity_type_model.create(
            {
                "name": "Act Type Without Default Responsible",
                "res_model": cls.partner_ir_model.model,
                "default_user_id": False,
            }
        )
        cls.activity_type_2 = activity_type_model.create(
            {
                "name": "Act Type 2",
                "res_model": cls.partner_ir_model.model,
                "default_user_id": False,
            }
        )
        cls.act1 = (
            cls.env["mail.activity"]
            .with_user(cls.user_2)
            .create(
                {
                    "activity_type_id": cls.activity_type_1.id,
                    "note": "Partner activity 1.",
                    "res_id": cls.partner_01.id,
                    "res_model_id": cls.partner_ir_model.id,
                    "user_id": cls.user_2.id,
                }
            )
        )
        cls.act2 = (
            cls.env["mail.activity"]
            .with_user(cls.user_2)
            .create(
                {
                    "activity_type_id": cls.activity_type_2.id,
                    "note": "Partner activity 2.",
                    "res_id": cls.partner_01.id,
                    "res_model_id": cls.partner_ir_model.id,
                    "user_id": cls.user_2.id,
                }
            )
        )

    def test_activity_default_user(self):
        self.act1._onchange_activity_type_id()
        # by default user is set to current user.
        self.assertEqual(self.act1.user_id, self.user_2)

    def test_activity_user_retained_on_type_change(self):
        # Simulate a change in activity type with no default user set
        original_user_id = self.act1.user_id
        self.act1.activity_type_id = self.activity_type_2  # Change activity type
        self.act1._onchange_activity_type_id()

        # Check if user_id has not changed
        self.assertEqual(
            self.act1.user_id, original_user_id, "The user should not be changed."
        )

    def test_schedule_new_activity_user(self):
        prev_act_uid = self.act1.create_uid
        action = self.act1.action_feedback_schedule_next()
        new_act = self.env["mail.activity"].with_context(**action["context"]).create({})
        # by default current user will be responsible.
        # module set responsible as prev. activity creator.
        self.assertEqual(new_act.user_id, prev_act_uid)

        self.act2.action_feedback_schedule_next()

    def test_default_get_user_assignment(self):
        # Simulate context where previous activity creator is assigned
        self.env.context = dict(
            self.env.context, source_activity_create_uid=self.user_2.id
        )
        activity = self.env["mail.activity"].default_get(["user_id"])

        # Assert that the user_id is set to the previous activity creator
        self.assertEqual(
            activity["user_id"],
            self.user_2.id,
            "The user_id should be assigned to the previous activity creator.",
        )
