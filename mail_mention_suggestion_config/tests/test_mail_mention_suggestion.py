# Copyright 2026 Alberto Martínez <alberto.martinez@sygel.es>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo.tests.common import TransactionCase


class TestMailMentionSuggestion(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner_model = cls.env["res.partner"]
        cls.company = cls.env.ref("base.main_company")
        cls.user_admin = cls.env.ref("base.user_admin")
        cls.user_demo = cls.env.ref("base.user_demo")
        cls.user_portal = cls.env.ref("base.demo_user0")
        cls.env["res.users"].search(
            [
                (
                    "id",
                    "not in",
                    [cls.user_admin.id, cls.user_demo.id, cls.user_portal.id],
                )
            ]
        ).write({"active": False})

    def test_mail_mention_suggestion_users(self):
        self.company.write({"mail_mention_suggestion_option": "users"})
        partners = self.partner_model.get_mention_suggestions("")["res.partner"]
        self.assertEqual(len(partners), 3)

    def test_mail_mention_suggestion_internal_users(self):
        self.company.write({"mail_mention_suggestion_option": "users_internal"})
        partners = self.partner_model.get_mention_suggestions("")["res.partner"]
        self.assertEqual(len(partners), 2)
