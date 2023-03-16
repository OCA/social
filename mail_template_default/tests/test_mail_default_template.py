# Copyright 2023 Solvti sp. z o.o. (https://solvti.pl)

from odoo.tests import TransactionCase


class TestMailDefaultTemplateRule(TransactionCase):
    def setUp(self):
        super(TestMailDefaultTemplateRule, self).setUp()
        self.context = {
            "default_model": "res.users",
            "default_res_id": self.env.ref("base.user_admin").id,
        }
        self.rule_id = self.env["mail.template.rule"].create(
            {
                "name": "Rule Default",
                "model_id": self.env["ir.model"]
                .search([("model", "=", "res.users")])
                .id,
                "template_id": self.env.ref("auth_signup.reset_password_email").id,
            }
        )

    def test_context_flag_and_sequence_order(self):
        rule2 = self.rule_id.copy(
            {"template_id": self.env.ref("auth_signup.set_password_email").id}
        )
        rule2.write({"context_flag": "set_password", "sequence": 0})
        # context force_mail_template = set_password
        composer_id = (
            self.env["mail.compose.message"]
            .with_context(**{**self.context, "force_mail_template": "set_password"})
            .create({})
        )
        self.assertEqual(composer_id.template_id, rule2.template_id)

        # context force_mail_template = False
        composer_id = (
            self.env["mail.compose.message"]
            .with_context(**{**self.context, "force_mail_template": False})
            .create({})
        )
        self.assertFalse(composer_id.template_id)

        # context None
        composer_id = (
            self.env["mail.compose.message"].with_context(**self.context).create({})
        )
        self.assertEqual(composer_id.template_id, self.rule_id.template_id)

    def test_field_domain(self):
        self.rule_id.write({"field_domain": "[['login','=','admin']]"})

        composer_id = (
            self.env["mail.compose.message"].with_context(**self.context).create({})
        )
        self.assertEqual(composer_id.template_id, self.rule_id.template_id)

        composer_id = (
            self.env["mail.compose.message"]
            .with_context(
                **{**self.context, "default_res_id": self.env.ref("base.user_demo").id}
            )
            .create({})
        )
        self.assertFalse(composer_id.template_id)

    def test_company(self):
        company2 = self.env["res.company"].create({"name": "company 2"})
        user2 = (
            self.env["res.users"]
            .with_company(company2.id)
            .create(
                {
                    "name": "user2",
                    "login": "user2",
                }
            )
        )
        rule2 = self.rule_id.copy(
            {"template_id": self.env.ref("auth_signup.set_password_email").id}
        )
        rule2.write({"company_id": company2.id})

        composer_id = (
            self.env["mail.compose.message"].with_context(**self.context).create({})
        )
        self.assertEqual(composer_id.template_id, self.rule_id.template_id)

        composer_id = (
            self.env["mail.compose.message"]
            .with_context(**{**self.context, "default_res_id": user2.id})
            .create({})
        )
        self.assertEqual(composer_id.template_id, rule2.template_id)
