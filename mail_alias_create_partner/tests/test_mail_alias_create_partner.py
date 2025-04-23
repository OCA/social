# Copyright 2025 Hunki Enterprises BV
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl-3.0)

from odoo import exceptions
from odoo.tests.common import TransactionCase

FROM_MAIL = "unknown_partner@test.com"
MAIL = f"""From: {FROM_MAIL}
To: mail_alias_create_partner@odoo.com
Subject: My mail

Hello"""


class TestMailAliasCreatePartner(TransactionCase):
    def setUp(self):
        super().setUp()
        self.parent_partner = self.env.ref("base.main_partner")
        self.alias = self.env["mail.alias"].create(
            {
                "alias_name": "mail_alias_create_partner",
                "alias_model_id": self.env["ir.model"]._get("mail.channel").id,
                "alias_create_partner": True,
                "alias_create_partner_defaults": "{'parent_id': %d, 'type': 'contact'}"
                % self.parent_partner.id,
            }
        )

    def test_partner_creation(self):
        """Test that a partner is created for aliases configured to do so"""
        self.assertFalse(self.env["res.partner"].search([("email", "=", FROM_MAIL)]))
        self.env["mail.thread"].message_process(None, MAIL)
        partner = self.env["res.partner"].search([("email", "=", FROM_MAIL)])
        self.assertTrue(partner)
        self.assertEqual(partner.parent_id, self.parent_partner)

    def test_malformed_from(self):
        """Test that we do nothing if there is no usable from header"""
        partners = self.env["res.partner"].search([])
        self.env["mail.thread"].message_process(None, MAIL.replace(FROM_MAIL, ""))
        self.assertEqual(partners, self.env["res.partner"].search([]))

    def test_no_partner_creation(self):
        """Test that no partner is created for aliases not configured to do so"""
        self.assertFalse(self.env["res.partner"].search([("email", "=", FROM_MAIL)]))
        self.alias.alias_create_partner = False
        self.env["mail.thread"].message_process(None, MAIL)
        self.assertFalse(self.env["res.partner"].search([("email", "=", FROM_MAIL)]))

    def test_partner_creation_with_name(self):
        """Test that names from from: header are used"""
        from_mail_name = "From Mail Name"
        self.assertFalse(self.env["res.partner"].search([("email", "=", FROM_MAIL)]))
        self.env["mail.thread"].message_process(
            None, MAIL.replace(FROM_MAIL, f"{from_mail_name} <{FROM_MAIL}>")
        )
        partner = self.env["res.partner"].search([("email", "=", FROM_MAIL)])
        self.assertEqual(partner.name, from_mail_name)

    def test_constraints(self):
        """Test constraint functions"""
        with self.assertRaises(exceptions.ValidationError):
            self.alias.alias_create_partner_defaults = "wrong value"
