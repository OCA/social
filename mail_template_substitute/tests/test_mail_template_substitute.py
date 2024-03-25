# Copyright 2019 ACSONE SA/NV
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo.tests.common import Form, TransactionCase


class TestMailTemplateSubstitute(TransactionCase):
    def setUp(self):
        super().setUp()
        self.smt2 = self.env["mail.template"].create(
            {
                "name": "substitute_template_2",
                "model_id": self.env.ref("base.model_res_partner").id,
            }
        )
        self.smt1 = self.env["mail.template"].create(
            {
                "name": "substitute_template_1",
                "model_id": self.env.ref("base.model_res_partner").id,
                "mail_template_substitution_rule_ids": [
                    (
                        0,
                        0,
                        {
                            "substitution_mail_template_id": self.smt2.id,
                            "domain": "[('id', '=', False)]",
                        },
                    )
                ],
            }
        )
        self.mt = self.env["mail.template"].create(
            {
                "name": "base_template",
                "model_id": self.env.ref("base.model_res_partner").id,
                "mail_template_substitution_rule_ids": [
                    (0, 0, {"substitution_mail_template_id": self.smt1.id})
                ],
            }
        )
        self.mail_compose = self.env["mail.compose.message"].create(
            {"template_id": self.mt.id, "composition_mode": "mass_mail"}
        )
        self.partners = self.env["res.partner"].search([])
        self.partner = self.env["res.partner"].search([], limit=1)

    def test_get_email_template_partners(self):
        self.assertEqual(
            self.mt._get_substitution_template(
                self.env.ref("base.model_res_partner"), self.partners.ids
            ),
            self.smt1,
        )
        res_ids_to_templates = self.mt._classify_per_lang(self.partners.ids)
        self.assertTrue(len(res_ids_to_templates))
        _lang, (template, _res_ids) = list(res_ids_to_templates.items())[0]
        self.assertEqual(
            template,
            self.smt1,
        )

    def test_get_email_template_partner(self):
        self.assertEqual(
            self.mt._get_substitution_template(
                self.env.ref("base.model_res_partner"), self.partner.ids
            ),
            self.smt1,
        )
        res_ids_to_templates = self.mt._classify_per_lang(self.partner.ids)
        self.assertTrue(len(res_ids_to_templates))
        _lang, (template, _res_ids) = list(res_ids_to_templates.items())[0]
        self.assertEqual(
            template,
            self.smt1,
        )

    def test_get_substitution_template(self):
        self.assertEqual(
            self.mail_compose.with_context(
                active_ids=self.partners.ids
            )._get_substitution_template("mass_mail", self.mt, None),
            self.smt1,
        )

    def test_default_get(self):
        mail_compose_form = Form(
            self.env["mail.compose.message"].with_context(
                **{
                    "default_template_id": self.mt.id,
                    "default_model": self.partner._name,
                    "default_res_ids": self.partner.ids,
                }
            )
        )
        self.assertEqual(mail_compose_form.template_id, self.smt1)
