# Copyright 2015 Pedro M. Baeza <pedro.baeza@tecnativa.com>
# Copyright 2015 Antonio Espinosa <antonio.espinosa@tecnativa.com>
# Copyright 2015 Javier Iniesta <javieria@antiun.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from . import base
from ..hooks import post_init_hook
from odoo.exceptions import ValidationError


class MailMassMailingContactCase(base.BaseCase):

    def test_match_existing_contacts(self):
        contact = self.create_mailing_contact(
            {'email': 'partner@test.com',
             'list_ids': [(6, 0, self.mailing_list.ids)]})
        post_init_hook(self.cr, self.registry)
        self.assertEqual(contact.partner_id.id, self.partner.id)
        self.check_mailing_contact_partner(contact)

    def test_create_mass_mailing_contact(self):
        title_doctor = self.env.ref('base.res_partner_title_doctor')
        country_cu = self.env.ref('base.cu')
        category_4 = self.env.ref('base.res_partner_category_4')
        category_5 = self.env.ref('base.res_partner_category_5')
        contact_vals = {
            'name': 'Partner test 2', 'email': 'partner2@test.com',
            'title_id': title_doctor.id, 'company_name': "TestCompany",
            'country_id': country_cu.id,
            'tag_ids': [(6, 0, (category_4 | category_5).ids)],
            'list_ids': [(6, 0, (self.mailing_list | self.mailing_list2).ids)],
        }
        contact = self.create_mailing_contact(contact_vals)
        self.check_mailing_contact_partner(contact)
        with self.assertRaises(ValidationError):
            self.create_mailing_contact(
                {'email': 'partner2@test.com',
                 'list_ids': [[6, 0, [self.mailing_list2.id]]]})

    def test_write_mass_mailing_contact(self):
        contact = self.create_mailing_contact(
            {'email': 'partner@test.com',
             'list_ids': [(6, 0, self.mailing_list.ids)]})
        contact.write({'partner_id': False})
        self.check_mailing_contact_partner(contact)
        contact2 = self.create_mailing_contact(
            {'email': 'partner2@test.com', 'name': 'Partner test 2',
             'list_ids': [(6, 0, self.mailing_list.ids)]})
        contact2.write({'partner_id': False})
        self.assertFalse(contact2.partner_id)

    def test_onchange_partner(self):
        contact = self.create_mailing_contact(
            {'email': 'partner@test.com',
             'list_ids': [[6, 0, [self.mailing_list.id]]]})
        title_doctor = self.env.ref('base.res_partner_title_doctor')
        country_cu = self.env.ref('base.cu')
        category_4 = self.env.ref('base.res_partner_category_4')
        category_5 = self.env.ref('base.res_partner_category_5')
        partner_vals = {
            'name': 'Partner test 2', 'email': 'partner2@test.com',
            'title': title_doctor.id, 'company_id': self.main_company.id,
            'country_id': country_cu.id,
            'category_id': [(6, 0, (category_4 | category_5).ids)],
        }
        partner = self.create_partner(partner_vals)
        with self.env.do_in_onchange():
            contact.partner_id = partner
            contact._onchange_partner_mass_mailing_partner()
            self.check_mailing_contact_partner(contact)
