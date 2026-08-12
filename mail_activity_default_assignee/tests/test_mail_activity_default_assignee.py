from odoo.tests import Form
from odoo.tests.common import TransactionCase


class TestMailActivityDefaultAssignee(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        create_uid = cls.env["ir.model.fields"].search(
            [("name", "=", "create_uid"), ("model", "=", "res.partner")], limit=1
        )
        cls.todo_act_type = cls.env["mail.activity.type"].create(
            {
                "name": "Custom To-Do",
                "category": "default",
                "res_model": "res.partner",
                "default_user_field_id": create_uid.id,
            }
        )

    def test_mail_activity_default_assignee(self):
        odoobot = self.env.ref("base.user_root")
        wizard_form = Form(
            self.env["mail.activity.schedule"]
            .with_context(
                active_ids=self.env.ref("base.res_partner_1").ids,
                active_id=self.env.ref("base.res_partner_1").ids[:1],
                active_model="res.partner",
            )
            .create(
                {
                    "activity_type_id": self.todo_act_type.id,
                }
            )
        )
        self.assertEqual(wizard_form.activity_user_id, odoobot)
