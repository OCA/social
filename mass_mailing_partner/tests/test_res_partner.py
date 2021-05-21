# Copyright 2015 Pedro M. Baeza <pedro.baeza@tecnativa.com>
# Copyright 2015 Antonio Espinosa <antonio.espinosa@tecnativa.com>
# Copyright 2015 Javier Iniesta <javieria@antiun.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from . import base
from odoo.exceptions import ValidationError


class ResPartnerCase(base.BaseCase):

    def test_count_mass_mailing_contacts(self):
        self.create_mailing_contact(
            {'email': 'partner@test.com',
             'list_ids': [[6, 0, [self.mailing_list.id]]]})
        self.create_mailing_contact(
            {'email': 'partner@test.com',
             'list_ids': [[6, 0, [self.mailing_list2.id]]]})
        self.assertEqual(self.partner.mass_mailing_contacts_count, 2)

    def test_write_res_partner(self):
        contact = self.create_mailing_contact(
            {'email': 'partner@test.com',
             'list_ids': [[6, 0, [self.mailing_list.id]]]})
        self.assertEqual(self.partner, contact.partner_id)

        title_doctor = self.env.ref('base.res_partner_title_doctor')
        country_cu = self.env.ref('base.cu')
        category_4 = self.env.ref('base.res_partner_category_4')
        category_5 = self.env.ref('base.res_partner_category_5')
        self.partner.write({
            'name': 'Changed', 'email': 'partner@changed.com',
            'title': title_doctor.id, 'company_id': self.main_company.id,
            'country_id': country_cu.id,
            'category_id': [(6, 0, (category_4 | category_5).ids)],
        })
        self.check_mailing_contact_partner(contact)
        with self.assertRaises(ValidationError):
            self.partner.write({'email': False})
