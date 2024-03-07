# Copyright 2015 Pedro M. Baeza <pedro.baeza@tecnativa.com>
# Copyright 2015 Antonio Espinosa <antonio.espinosa@tecnativa.com>
# Copyright 2015 Javier Iniesta <javieria@antiun.com>
# Copyright 2020 Tecnativa - Manuel Calero
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo.tests.common import TransactionCase


class BaseCase(TransactionCase):
    def setUp(self):
        super().setUp()

        self.main_company = self.env.ref("base.main_company")
        self.country_es = self.env.ref("base.es")
        self.category_0 = self.env.ref("base.res_partner_category_0")
        self.category_2 = self.env.ref("base.res_partner_category_2")
        self.title_mister = self.env.ref("base.res_partner_title_mister")
        self.partner = self.create_partner(
            {
                "name": "Partner test",
                "email": "partner@test.com",
                "title": self.title_mister.id,
                "company_id": self.main_company.id,
                "country_id": self.country_es.id,
                "category_id": [(6, 0, (self.category_0 | self.category_2).ids)],
            }
        )

        self.category_3 = self.env.ref("base.res_partner_category_3")
        self.mailing_list = self.create_mailing_list({"name": "List test"})
        self.mailing_list2 = self.create_mailing_list(
            {
                "name": "List test 2",
                "partner_mandatory": True,
                "partner_category": self.category_3.id,
            }
        )

    def create_partner(self, vals):
        m_partner = self.env["res.partner"]
        return m_partner.create(vals)

    def create_mailing_contact(self, vals):
        m_mailing_contact = self.env["mailing.contact"]
        return m_mailing_contact.create(vals)

    def create_mailing_list(self, vals):
        m_mailing_list = self.env["mailing.list"]
        return m_mailing_list.create(vals)

    def check_mailing_contact_partner(self, mailing_contact):
        if mailing_contact.partner_id:
            self.assertEqual(mailing_contact.partner_id.email, mailing_contact.email)
            self.assertEqual(mailing_contact.partner_id.name, mailing_contact.name)
            self.assertEqual(mailing_contact.partner_id.title, mailing_contact.title_id)
            if mailing_contact.partner_id.company_id:
                self.assertEqual(
                    mailing_contact.partner_id.company_id.name,
                    mailing_contact.company_name,
                )
            self.assertEqual(
                mailing_contact.partner_id.country_id, mailing_contact.country_id
            )
            self.assertEqual(
                mailing_contact.partner_id.category_id, mailing_contact.tag_ids
            )
