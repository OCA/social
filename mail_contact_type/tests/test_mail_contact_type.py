# Copyright 2022 Foodles (http://www.foodles.co).
# @author Pierre Verkest <pierreverkest84@gmail.com>
# @author Matthias Barkat <matthias.barkat@foodles.co>
# @author Alexandre Galdeano <alexandre.galdeano@foodles.co>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo.tests.common import SavepointCase


class TestMailContactType(SavepointCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.mail_contact_type_invoice = cls.env["mail.contact.type"].create(
            {
                "name": "Invoice",
                "code": "invoice",
            }
        )
        cls.mail_contact_type_sale = cls.env["mail.contact.type"].create(
            {
                "name": "Sale",
                "code": "sale",
            }
        )
        cls.mail_contact_type_purchase = cls.env["mail.contact.type"].create(
            {
                "name": "Purchase",
                "code": "purchase",
            }
        )
        cls.mail_contact_type_communication = cls.env["mail.contact.type"].create(
            {
                "name": "Communication",
                "code": "communication",
            }
        )

        #                    THE COMPANY (invoice)
        #                        |
        # ---------------------------------------------------
        # |               |               |                 |
        # |               |               |                 |
        # partner1        partner2        partner3          partner4
        # [invoice]       [sale]          [purchase]        [invoice,sale]

        cls.main_partner = cls.env["res.partner"].create(
            {
                "name": "The company",
                "email": "contact@company.com",
                "is_company": True,
                "mail_contact_type_ids": [(6, 0, [cls.mail_contact_type_invoice.id])],
            }
        )
        cls.partner1 = cls.env["res.partner"].create(
            {
                "name": "partner1",
                "email": "partner1@company.com",
                "parent_id": cls.main_partner.id,
                "mail_contact_type_ids": [(6, 0, [cls.mail_contact_type_invoice.id])],
            }
        )
        cls.partner2 = cls.env["res.partner"].create(
            {
                "name": "partner2",
                "email": "partner2@company.com",
                "parent_id": cls.main_partner.id,
                "mail_contact_type_ids": [(6, 0, [cls.mail_contact_type_sale.id])],
            }
        )
        cls.partner3 = cls.env["res.partner"].create(
            {
                "name": "partner3",
                "email": "partner3@company.com",
                "parent_id": cls.main_partner.id,
                "mail_contact_type_ids": [(6, 0, [cls.mail_contact_type_purchase.id])],
            }
        )
        cls.partner4 = cls.env["res.partner"].create(
            {
                "name": "partner4",
                "email": "partner4@company.com",
                "parent_id": cls.main_partner.id,
                "mail_contact_type_ids": [
                    (
                        6,
                        0,
                        [
                            cls.mail_contact_type_invoice.id,
                            cls.mail_contact_type_sale.id,
                        ],
                    )
                ],
            }
        )

    def test_find_contacts_by_mail_contact_type(self):
        self.assertEqual(
            self.main_partner._find_contacts_by_mail_contact_types(["invoice"]),
            self.partner1 | self.partner4 | self.main_partner,
        )
        self.assertEqual(
            self.main_partner._find_contacts_by_mail_contact_types(["sale"]),
            self.partner2 | self.partner4,
        )
        self.assertEqual(
            self.main_partner._find_contacts_by_mail_contact_types(["purchase"]),
            self.partner3,
        )
        self.assertEqual(
            self.main_partner._find_contacts_by_mail_contact_types(["communication"]),
            self.env["res.partner"],
        )
        self.assertEqual(
            self.main_partner._find_contacts_by_mail_contact_types(["invoice", "sale"]),
            self.partner1 | self.partner2 | self.partner4 | self.main_partner,
        )

    def test_contact_by_type(self):
        self.assertEqual(
            self.main_partner.contact_by_types("invoice"),
            f"{self.partner1.id},{self.partner4.id},{self.main_partner.id}",
        )
        self.assertEqual(
            self.main_partner.contact_by_types("sale"),
            f"{self.partner2.id},{self.partner4.id}",
        )
        self.assertEqual(
            self.main_partner.contact_by_types("purchase"),
            f"{self.partner3.id}",
        )
        self.assertEqual(
            self.main_partner.contact_by_types("communication"),
            "",
        )
        self.assertEqual(
            self.main_partner.contact_by_types("invoice", "sale"),
            f"{self.partner1.id},{self.partner2.id},{self.partner4.id},{self.main_partner.id}",
        )

    def test_get_name(self):
        self.assertEqual(
            self.main_partner._get_name(),
            "The company",
        )
        self.assertEqual(
            self.main_partner.with_context(show_mail_contact_types=True)._get_name(),
            "The company (Invoice)",
        )
        self.assertEqual(
            self.partner1.with_context(show_mail_contact_types=True)._get_name(),
            "The company, partner1 (Invoice)",
        )
        self.assertEqual(
            self.partner2.with_context(show_mail_contact_types=True)._get_name(),
            "The company, partner2 (Sale)",
        )
        self.assertEqual(
            self.partner3.with_context(show_mail_contact_types=True)._get_name(),
            "The company, partner3 (Purchase)",
        )
        self.assertEqual(
            self.partner4.with_context(show_mail_contact_types=True)._get_name(),
            "The company, partner4 (Invoice, Sale)",
        )

    def test_name_search_by_contact_type(self):
        self.assertEqual(
            self.env["res.partner"]
            .with_context(show_mail_contact_types=True)
            .name_search(name="Invoice"),
            [
                (self.main_partner.id, "The company (Invoice)"),
                (self.partner1.id, "The company, partner1 (Invoice)"),
                (self.partner4.id, "The company, partner4 (Invoice, Sale)"),
            ],
        )

    def test_name_search_by_contact_type_insensitive_case(self):
        self.assertEqual(
            self.env["res.partner"]
            .with_context(show_mail_contact_types=True)
            .name_search(name="invoice"),
            [
                (self.main_partner.id, "The company (Invoice)"),
                (self.partner1.id, "The company, partner1 (Invoice)"),
                (self.partner4.id, "The company, partner4 (Invoice, Sale)"),
            ],
        )

    def test_name_search_by_contact_type_partial_type_name(self):
        self.assertEqual(
            self.env["res.partner"]
            .with_context(show_mail_contact_types=True)
            .name_search(name="invo"),
            [],
        )

    def test_name_search_by_contact_type_without_show_mail_contact_types_context(self):
        self.assertEqual(self.env["res.partner"].name_search(name="invoice"), [])
