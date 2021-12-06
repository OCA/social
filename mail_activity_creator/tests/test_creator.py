# Copyright 2020 Creu Blanca
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).


from odoo.tests.common import TransactionCase


class TestCreator(TransactionCase):
    def setUp(self):
        super().setUp()

        self.partner = self.env["res.partner"].create({"name": "DEMO"})
        self.user_01 = self.env["res.users"].create(
            {
                "name": "user_01",
                "login": "demo_user_01",
                "email": "demo@demo.de",
                "notification_type": "inbox",
            }
        )
        self.partner_model = self.env["ir.model"]._get("res.partner")
        self.ActivityType = self.env["mail.activity.type"]
        self.activity1 = self.ActivityType.create(
            {
                "name": "Initial Contact",
                "delay_count": 5,
                "summary": "ACT 1 : Presentation, barbecue, ... ",
                "res_model": self.partner_model.model,
            }
        )

    def test_activity_creator(self):
        activity = (
            self.env["mail.activity"]
            .sudo()
            .with_user(self.user_01.id)
            .create(
                {
                    "activity_type_id": self.activity1.id,
                    "note": "Partner activity 3.",
                    "res_id": self.partner.id,
                    "res_model_id": self.partner_model.id,
                    "user_id": self.user_01.id,
                }
            )
        )
        self.assertEqual(activity.creator_uid, self.user_01)
