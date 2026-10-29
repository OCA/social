# Copyright 2023 Ooops404
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
from odoo.tests.common import TransactionCase, new_test_user


class TestMailActivityReplyCreator(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # disable tracking test suite wise
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))
        # Internal users cannot write partners in 18.0; activity create
        # requires write (or mail_post_access) on the related document.
        cls.user_2 = new_test_user(
            cls.env,
            login="activity_assignee",
            groups="base.group_user,base.group_partner_manager",
            context={"no_reset_password": True, "tracking_disable": True},
        )
        cls.partner_ir_model = cls.env["ir.model"]._get("res.partner")
        cls.partner_01 = cls.env["res.partner"].create({"name": "Activity Partner"})
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
        # module keeps original activity user, if activity type has no default_user_id.
        self.assertEqual(self.act1.user_id, self.user_2)

    def test_schedule_new_activity_user(self):
        prev_act_uid = self.act1.create_uid
        action = self.act1.action_feedback_schedule_next()
        new_act = self.env["mail.activity"].with_context(**action["context"]).create({})
        # by default current user will be responsible.
        # module set responsible as prev. activity creator.
        self.assertEqual(new_act.user_id, prev_act_uid)
        self.act2.action_feedback_schedule_next()
