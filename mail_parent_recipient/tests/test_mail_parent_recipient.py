# -*- coding: utf-8 -*-
# Copyright 2018 Camptocamp
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo.addons.mail.tests.common import TestMail


class TestMailTemplate(TestMail):

    def setUp(self):
        super(TestMailTemplate, self).setUp()

        self.Users = self.env['res.users']
        self.res_parter = self.env['res.partner']
        self.mail_template = self.env['mail.template']
        self.mail_comp_msg = self.env['mail.compose.message']

        # Company
        company_vals = {
            'name': 'company_name_test',
            'email': 'company.mail.test@company'
        }

        self.company_test = self.res_parter.create(company_vals)

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

        self.partner_no_mail = self.res_parter.create(partner_no_mail_vals)
        self.partner_with_mail = self.res_parter.create(partner_with_mail_vals)

    def create_mail_composer(self, partner_to_send_id):
        self.email_template = self.env['mail.template'].create({
            'model_id': self.env['ir.model'].search([
                ('model', '=', 'mail.channel')
            ], limit=1).id,
            'name': 'Pigs Template',
            'subject': '${object.name}',
            'body_html': '${object.description}',
            'user_signature': False,
            'partner_to': '%s' % (partner_to_send_id),
        })

        self.composer = self.mail_comp_msg.with_context({
            'default_composition_mode': 'comment',
            'default_model': 'mail.channel',
            'default_use_template': True,
        }).create({
            'subject': 'Forget me subject',
            'body': 'Dummy body',
            'template_id': self.email_template.id
        })

        return self.composer

    # def test_1_mail_send_to_partner_no_mail(self):
    #     """
    #     Mail should only send with company mail
    #     even if is sended to partner_no_mail
    #     """
    #     import pdb; pdb.set_trace()
    #     mail_composer = self.create_mail_composer(self.partner_no_mail.id)
    #     mail_id = self.email_template.send_mail(self.partner_no_mail.id)
    #     mail = self.env['mail.mail'].browse(mail_id)
    #
    #     self.assertEqual(mail.recipient_ids, self.company_test.id)
    #     self.assertNotEqual(mail.recipient_ids, self.partner_no_mail.id)
    #     self.assertNotEqual(mail.recipient_ids, self.partner_with_mail.id)
    #     self.assertEqual(len(mail.recipient_ids), 1)
    #
    # def test_2_mail_send_to_partner_with_mail(self):
    #     """
    #     Mail should only send with company mail
    #     even if is sended to partner_with_mail
    #     """
    #     mail_composer = self.create_mail_composer(self.partner_no_mail.id)
    #     mail_id = self.email_template.send_mail(self.partner_with_mail.id)
    #     mail = self.env['mail.mail'].browse(mail_id)
    #
    #     self.assertEqual(mail.recipient_ids, self.company_test.id)
    #     self.assertNotEqual(mail.recipient_ids, self.partner_no_mail.id)
    #     self.assertNotEqual(mail.recipient_ids, self.partner_with_mail.id)
    #     self.assertEqual(len(mail.recipient_ids), 1)
    #
    # def test_3_mail_send_to_company_test(self):
    #     """
    #     Mail should only send with company mail
    #     """
    #     mail_composer = self.create_mail_composer(self.partner_no_mail.id)
    #     mail_id = self.email_template.send_mail(self.company_test.id)
    #     mail = self.env['mail.mail'].browse(mail_id)
    #
    #     self.assertEqual(mail.recipient_ids, self.company_test.id)
    #     self.assertNotEqual(mail.recipient_ids, self.partner_no_mail.id)
    #     self.assertNotEqual(mail.recipient_ids, self.partner_with_mail.id)
    #     self.assertEqual(len(mail.recipient_ids), 1)
