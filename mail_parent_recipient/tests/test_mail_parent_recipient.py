# -*- coding: utf-8 -*-
# Copyright 2018 Camptocamp
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo.addons.mail.tests.common import TestMail


class TestMailTemplate(TestMail):

    def setUp(self):
        super(TestMailTemplate, self).setUp()

        self.Users = self.env['res.users']
        self.res_partner = self.env['res.partner']
        self.mail_template = self.env['mail.template']
        self.mail_comp_msg = self.env['mail.compose.message']

        # Company
        company_vals = {
            'name': 'company_name_test',
            'email': 'company.mail.test@company'
        }

        self.company_test = self.res_partner.create(company_vals)

        # Partners test 1 without email
        partner_no_mail_vals = {
            'name': 'partner_1',
            'parent_id': self.company_test.id,
        }

        # Partners test 2 with email
        partner_with_mail_vals = {
            'name': 'partner_2',
            'email': 'partner.2.mail.test@company',
            'parent_id': self.company_test.id,
        }

        self.partner_no_mail = self.res_partner.create(partner_no_mail_vals)
        self.partner_with_mail = self.res_partner.create(partner_with_mail_vals)

    def create_mail_composer(self, partner_to_send_id):
        email_template = self.env['mail.template'].create({
            'model_id': self.env['ir.model'].search([
                ('model', '=', 'mail.channel')
            ], limit=1).id,
            'name': 'Pigs Template',
            'subject': '${object.name}',
            'body_html': '${object.description}',
            'user_signature': False,
            'partner_to': '%s' % (partner_to_send_id),
        })

        composer = self.mail_comp_msg.with_context({
            'default_composition_mode': 'comment',
            'default_model': 'mail.channel',
            'default_use_template': True,
        }).create({
            'subject': 'Forget me subject',
            'body': 'Dummy body',
            'template_id': email_template.id
        })
        values = composer.onchange_template_id(
            email_template.id,
            'comment', 'mail.channel', self.group_pigs.id
        )['value']

        # use _convert_to_cache to return a browse record list from command list or id list for x2many fields
        values = composer._convert_to_record(composer._convert_to_cache(values))
        recipients = values['partner_ids']

        return recipients

    def test_1_mail_send_to_partner_no_mail(self):
        """
        Mail should only send with company mail
        even if is sended to partner_no_mail
        """
        recipients = self.create_mail_composer(self.partner_no_mail.id)

        self.assertEqual(recipients.email, self.company_test.email)
        self.assertNotEqual(recipients.email, self.partner_no_mail.email)
        self.assertNotEqual(recipients.email, self.partner_with_mail.email)

    def test_2_mail_send_to_partner_with_mail(self):
        """
        Mail should only send with company mail
        even if is sended to partner_with_mail
        """
        recipients = self.create_mail_composer(self.partner_with_mail.id)

        self.assertNotEqual(recipients.email, self.company_test.email)
        self.assertNotEqual(recipients.email, self.partner_no_mail.email)
        self.assertEqual(recipients.email, self.partner_with_mail.email)

    def test_3_mail_send_to_company_test(self):
        """
        Mail should only send with company mail
        """
        recipients = self.create_mail_composer(self.partner_no_mail.id)

        self.assertEqual(recipients.email, self.company_test.email)
        self.assertNotEqual(recipients.email, self.partner_no_mail.email)
        self.assertNotEqual(recipients.email, self.partner_with_mail.email)
