# Copyright 2019 ACSONE SA/NV
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo.tests.common import TransactionCase


class TestMailTemplateSubstitute(TransactionCase):
    def setUp(self):
        super(TestMailTemplateSubstitute, self).setUp()
        self.smt2 = self.env['mail.template'].create(
            {
                'name': 'substitute_template_2',
                'model_id': self.env.ref('base.model_res_partner').id,
            }
        )
        self.smt1 = self.env['mail.template'].create(
            {
                'name': 'substitute_template_1',
                'model_id': self.env.ref('base.model_res_partner').id,
                'mail_template_substitution_rule_ids': [
                    (
                        0,
                        0,
                        {
                            'substitution_mail_template_id': self.smt2.id,
                            'domain': "[('id', '=', False)]",
                        },
                    )
                ],
            }
        )
        self.mt = self.env['mail.template'].create(
            {
                'name': 'base_template',
                'model_id': self.env.ref('base.model_res_partner').id,
                'mail_template_substitution_rule_ids': [
                    (0, 0, {'substitution_mail_template_id': self.smt1.id})
                ],
            }
        )
        self.mail_compose = self.env['mail.compose.message'].create(
            {'template_id': self.mt.id, 'composition_mode': 'mass_mail'}
        )
        self.partners = self.env['res.partner'].search([])

    def test_get_email_template(self):
        self.assertEqual(
            self.mt._get_substitution_template(
                self.env.ref('base.model_res_partner'), self.partners.ids
            ),
            self.smt1,
        )
        self.assertEqual(
            self.mt.get_email_template(self.partners.ids).get(
                self.partners.ids[0]
            ),
            self.smt1,
        )

    def test_get_substitution_template(self):
        self.assertEqual(
            self.mail_compose.with_context(
                active_ids=self.partners.ids
            )._get_substitution_template('mass_mail', self.mt, None),
            self.smt1,
        )

    def test_onchange_template_id_wrapper(self):
        self.assertEqual(self.mail_compose.template_id, self.mt)
        self.smt1.mail_template_substitution_rule_ids.domain = '[]'
        self.mail_compose.with_context(
            active_ids=self.partners.ids
        ).onchange_template_id_wrapper()
        self.assertEqual(self.mail_compose.template_id, self.smt2)
