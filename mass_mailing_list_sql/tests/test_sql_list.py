# Copyright (C) 2023 ForgeFlow, S.L.
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from odoo.tests import common


class TestMassMailingSql(common.SavepointCase):
    post_install = True

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.tag = cls.env["res.partner.category"].create({"name": "testing tag"})
        cls.partners = cls.env["res.partner"]
        for number in range(5):
            cls.partners |= cls.partners.create(
                {
                    "name": "partner %d" % number,
                    "email": "%d@example.com" % number,
                    "country_id": 1,
                }
            )
        for number in range(6, 9):
            cls.partners |= cls.partners.create(
                {
                    "name": "partner %d" % number,
                    "email": "%d@example.com" % number,
                    "country_id": 2,
                }
            )

        cls.Partner = cls.env["res.partner"]
        cls.partner_in = cls.Partner.create(
            {
                "name": "Partner in",
                "email": "partner.in@example.com",
            }
        )
        cls.partner_out = cls.Partner.create(
            {
                "name": "Partner out",
                "email": "partner.out@example.com",
            }
        )

        cls.list = cls.env["mailing.list"].create(
            {
                "name": "test list",
                "sql_search": True,
                "query": "SELECT * FROM res_partner WHERE country_id = 1",
                "sync_method": "full",
            }
        )

    def test_mass_mailing_sql_1(self):
        """sql_search method returns correct partners."""
        self.list.flush()
        self.list.action_sync()
        self.list.flush()
        self.assertEqual(self.list.contact_nbr, 5)
        self.list.query = "SELECT * FROM res_partner WHERE country_id = 2"
        self.list.action_sync()
        self.list.flush()
        self.assertEqual(self.list.contact_nbr, 3)
        self.list.query = "SELECT * FROM res_partner WHERE country_id in (1,2)"
        self.list.action_sync()
        self.list.flush()
        self.assertEqual(self.list.contact_nbr, 8)

    def test_mass_mailing_sql_2(self):
        # Test sync_method and onchange methods
        self.list.write(
            {
                "sync_method": "full",
                "query": "SELECT id FROM res_partner WHERE email = 'partner.in@example.com'",
            }
        )

        self.list._onchange_dynamic()
        self.assertFalse(self.list.is_synced)

        self.list._onchange_query()
        self.list.button_validate_sql_expression()

        self.list.action_sync()
        self.assertIn(self.partner_in, self.list.contact_ids.mapped("partner_id"))
        self.assertNotIn(self.partner_out, self.list.contact_ids.mapped("partner_id"))
