# Copyright 2015 Tecnativa - Pedro M. Baeza
# Copyright 2015 Tecnativa - Antonio Espinosa
# Copyright 2015 Javier Iniesta <javieria@antiun.com>
# Copyright 2020 Tecnativa - Manuel Calero
# Copyright 2021 Tecnativa - Víctor Martínez
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo.exceptions import ValidationError

from . import base


class ResPartnerCase(base.BaseCase):
    def test_count_mass_mailing_contacts(self):
        self.create_mailing_contact(
            {"email": "partner@test.com", "list_ids": [[6, 0, [self.mailing_list.id]]]}
        )
        self.create_mailing_contact(
            {"email": "partner@test.com", "list_ids": [[6, 0, [self.mailing_list2.id]]]}
        )
        self.assertEqual(self.partner.mass_mailing_contacts_count, 2)

    def test_write_res_partner(self):
        contact = self.create_mailing_contact(
            {"email": "partner@test.com", "list_ids": [[6, 0, [self.mailing_list.id]]]}
        )
        self.assertEqual(self.partner, contact.partner_id)

        title_doctor = self.env.ref("base.res_partner_title_doctor")
        country_cu = self.env.ref("base.cu")
        category_8 = self.env.ref("base.res_partner_category_8")
        category_11 = self.env.ref("base.res_partner_category_11")
        self.partner.write(
            {
                "name": "Changed",
                "email": "partner@changed.com",
                "title": title_doctor.id,
                "company_id": self.main_company.id,
                "country_id": country_cu.id,
                "category_id": [(6, 0, (category_8 | category_11).ids)],
            }
        )
        self.check_mailing_contact_partner(contact)
        with self.assertRaises(ValidationError):
            self.partner.write({"email": False})

    def test_write_res_partner_multi(self):
        self.assertEqual(len(self.partner.category_id.ids), 2)
        partner2 = self.partner.copy({"name": "Partner test 2"})
        self.partner.write({"category_id": [(4, self.category_3.id)]})
        self.assertEqual(len(self.partner.category_id.ids), 3)
        self.assertEqual(len(partner2.category_id.ids), 2)
        for partner in [self.partner, partner2]:
            self.create_mailing_contact(
                {"partner_id": partner.id, "list_ids": [[6, 0, [self.mailing_list.id]]]}
            )
        self.env["res.partner"].search(
            [("id", "in", (self.partner.id, partner2.id))]
        ).write({"category_id": [(4, self.category_3.id)]})
        self.assertEqual(len(self.partner.category_id.ids), 3)
        self.assertEqual(len(partner2.category_id.ids), 3)
