# Copyright 2018 ForgeFlow S.L.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
from odoo.tests.common import SavepointCase


class TestMailActivityPartner(SavepointCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # disable tracking test suite wise
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))
        cls.user_model = cls.env["res.users"].with_context(no_reset_password=True)

        cls.user_admin = cls.env.ref("base.user_root")

        cls.employee = cls.env["res.users"].create(
            {
                "company_id": cls.env.ref("base.main_company").id,
                "name": "Employee",
                "login": "csu",
                "email": "crmuser@yourcompany.com",
                "groups_id": [
                    (
                        6,
                        0,
                        [
                            cls.env.ref("base.group_user").id,
                            cls.env.ref("base.group_partner_manager").id,
                        ],
                    )
                ],
            }
        )

        cls.partner_ir_model = cls.env["ir.model"]._get("res.partner")

        activity_type_model = cls.env["mail.activity.type"]
        cls.activity1 = activity_type_model.create(
            {
                "name": "Initial Contact",
                "delay_count": 5,
                "summary": "ACT 1 : Presentation, barbecue, ... ",
                "res_model_id": cls.partner_ir_model.id,
            }
        )
        cls.activity2 = activity_type_model.create(
            {
                "name": "Call for Demo",
                "delay_count": 6,
                "summary": "ACT 2 : I want to show you my ERP !",
                "res_model_id": cls.partner_ir_model.id,
            }
        )

        cls.partner_01 = cls.env.ref("base.res_partner_1")

        cls.homer = cls.env["res.partner"].create(
            {
                "name": "Homer Simpson",
                "city": "Springfield",
                "street": "742 Evergreen Terrace",
                "street2": "Donut Lane",
            }
        )

        # test synchro of street3 on create
        cls.partner_10 = cls.env["res.partner"].create(
            {"name": "Bart Simpson", "parent_id": cls.homer.id, "type": "contact"}
        )

    def test_partner_for_activity(self):

        self.act1 = (
            self.env["mail.activity"]
            .sudo()
            .create(
                {
                    "activity_type_id": self.activity1.id,
                    "note": "Partner activity 1.",
                    "res_id": self.partner_01.id,
                    "res_model_id": self.partner_ir_model.id,
                    "user_id": self.user_admin.id,
                }
            )
        )

        self.act2 = (
            self.env["mail.activity"]
            .with_user(self.employee)
            .create(
                {
                    "activity_type_id": self.activity2.id,
                    "note": "Partner activity 10.",
                    "res_id": self.partner_10.id,
                    "res_model_id": self.partner_ir_model.id,
                    "user_id": self.employee.id,
                }
            )
        )

        # Check partner_id of created activities
        self.assertEqual(self.act1.partner_id, self.partner_01)
        self.assertEqual(self.act2.partner_id, self.partner_10)

        # Check commercial_partner_id for created activities
        self.assertEqual(self.act1.commercial_partner_id, self.partner_01)
        self.assertEqual(self.act2.commercial_partner_id, self.homer)
