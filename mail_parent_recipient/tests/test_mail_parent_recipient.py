# -*- coding: utf-8 -*-
# Copyright 2018 Camptocamp
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo.addons.mail.tests.common import TestMail


class TestMailTemplate(TestMail):

    @classmethod
    def setUpClass(cls):
        super(TestMailTemplate, cls).setUpClass()

        cls.Users = cls.env['res.users']
        cls.res_partner = cls.env['res.partner']
        cls.mail_template = cls.env['mail.template']
        cls.mail_comp_msg = cls.env['mail.compose.message']

        # Company
        company_vals = {
            'name': 'company_name_test',
            'email': 'company.mail.test@company'
        }

        cls.company_test = cls.res_partner.create(company_vals)

        # Partners test 1 without email
        partner_no_mail_vals = {
            'name': 'partner_1',
            'parent_id': cls.company_test.id,
        }

        # Partners test 2 with email
        partner_with_mail_vals = {
            'name': 'partner_2',
            'email': 'partner.2.mail.test@company',
            'parent_id': cls.company_test.id,
        }

        cls.partner_no_mail = cls.res_partner.create(partner_no_mail_vals)
        cls.partner_with_mail = cls.res_partner.create(
            partner_with_mail_vals
        )

    def create_mail_composer(cls, partner_to_send_id):
        email_template = cls.env['mail.template'].create({
            'model_id': cls.env['ir.model'].search([
                ('model', '=', 'mail.channel')
            ], limit=1).id,
            'name': 'Pigs Template',
            'subject': '${object.name}',
            'body_html': '${object.description}',
            'user_signature': False,
            'partner_to': '%s' % (partner_to_send_id),
        })

        composer = cls.mail_comp_msg.with_context({
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
            'comment', 'mail.channel', cls.group_pigs.id
        )['value']

        # use _convert_to_cache to return a browse record list from command
        # list or id list for x2many fields
        values = composer._convert_to_record(
            composer._convert_to_cache(values)
        )
        recipients = values['partner_ids']

        return recipients

    def test_1_mail_send_to_partner_no_mail(cls):
        """Use company mail if recipient partner has no email."""
        recipients = cls.create_mail_composer(cls.partner_no_mail.id)

        cls.assertEqual(recipients.email, cls.company_test.email)
        cls.assertNotEqual(recipients.email, cls.partner_no_mail.email)
        cls.assertNotEqual(recipients.email, cls.partner_with_mail.email)

    def test_2_mail_send_to_partner_with_mail(cls):
        """Use partner mail if recipient partner has an email."""
        recipients = cls.create_mail_composer(cls.partner_with_mail.id)

        cls.assertNotEqual(recipients.email, cls.company_test.email)
        cls.assertNotEqual(recipients.email, cls.partner_no_mail.email)
        cls.assertEqual(recipients.email, cls.partner_with_mail.email)

    def test_3_mail_send_to_company_test(cls):
        """Use company mail if recipient is the company."""
        recipients = cls.create_mail_composer(cls.company_test.id)

        cls.assertEqual(recipients.email, cls.company_test.email)
        cls.assertNotEqual(recipients.email, cls.partner_no_mail.email)
        cls.assertNotEqual(recipients.email, cls.partner_with_mail.email)
