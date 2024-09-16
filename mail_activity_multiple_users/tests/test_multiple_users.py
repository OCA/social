# Copyright 2024 Binhex (<https://binhex.cloud>)
# Copyright 2024 Binhex Ariel Barreiros
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl)

from odoo.tests.common import SavepointCase


class TestMailActivityMultipleUsers(SavepointCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = cls.env["res.users"].create(
            {
                "company_id": cls.env.ref("base.main_company").id,
                "name": "User_01",
                "login": "user_01",
                "email": "user01@company.com",
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
        cls.user2 = cls.env["res.users"].create(
            {
                "company_id": cls.env.ref("base.main_company").id,
                "name": "User_02",
                "login": "user_02",
                "email": "user02@company.com",
                "groups_id": [(6, 0, [cls.env.ref("base.group_user").id])],
            }
        )

        cls.contact = cls.env["res.partner"].create(
            {"company_id": cls.env.ref("base.main_company").id, "name": "Contact"}
        )

        cls.activity_type = cls.env["mail.activity.type"].create(
            {
                "name": "Random Activity",
                "delay_count": 0,
                "delay_unit": "days",
                "res_model_id": cls.env.ref("base.model_res_partner").id,
            }
        )

        cls.activity = (
            cls.env["mail.activity"]
            .with_user(cls.user)
            .create(
                {
                    "activity_type_id": cls.activity_type.id,
                    "note": "This is a random content for activity",
                    "res_id": cls.contact.id,
                    "res_model_id": cls.env.ref("base.model_res_partner").id,
                    "user_id": cls.user.id,
                    "is_multiple_users_activity": True,
                    "user_ids": [(6, 0, [cls.user.id, cls.user2.id])],
                }
            )
        )

    def test_activities_created_for_users(self):
        user_ids = self.contact.activity_ids.mapped("user_id.id")
        self.assertIn(self.user.id, user_ids, "Activity should be created for user")
        self.assertIn(self.user2.id, user_ids, "Activity should be created for user2")

    def test_onchange_user_ids(self):
        self.activity.user_ids = [(6, 0, [self.user2.id, self.user.id])]
        self.activity._onchange_user_ids()
        self.assertEqual(
            self.activity.user_id.id,
            self.user2.id,
            "User ID should be set to the first user of user_ids",
        )
