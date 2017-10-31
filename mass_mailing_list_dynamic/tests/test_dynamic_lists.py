# -*- coding: utf-8 -*-
# Copyright 2017 Tecnativa - Jairo Llopis
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from mock import patch
from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase


class DynamicListCase(TransactionCase):
    def setUp(self):
        super(DynamicListCase, self).setUp()
        self.tag = self.env["res.partner.category"].create({
            "name": "testing tag",
        })
        self.partners = self.env["res.partner"]
        for number in range(5):
            self.partners |= self.partners.create({
                "name": "partner %d" % number,
                "category_id": [(4, self.tag.id, False)],
                "email": "%d@example.com" % number,
            })
        self.list = self.env["mail.mass_mailing.list"].create({
            "name": "test list",
            "dynamic": True,
            "sync_domain": repr([("category_id", "in", self.tag.ids)]),
        })
        self.mail = self.env["mail.mass_mailing"].create({
            "name": "test mass mailing",
            "contact_list_ids": [(4, self.list.id, False)],
        })
        self.mail._onchange_model_and_list()

    def test_list_sync(self):
        """List is synced correctly."""
        Contact = self.env["mail.mass_mailing.contact"]
        # Partner 0 is not categorized
        self.partners[0].category_id = False
        # Partner 1 has no email
        self.partners[1].email = False
        # Set list as unsynced
        self.list.dynamic = False
        # Create contact for partner 0 in unsynced list
        contact0 = Contact.create({
            "list_id": self.list.id,
            "partner_id": self.partners[0].id,
        })
        self.assertEqual(self.list.contact_nbr, 1)
        # Set list as add-synced
        self.list.dynamic = True
        self.list.action_sync()
        self.assertEqual(self.list.contact_nbr, 4)
        self.assertTrue(contact0.exists())
        # Set list as full-synced
        self.list.sync_method = "full"
        self.list.action_sync()
        self.assertEqual(self.list.contact_nbr, 3)
        self.assertFalse(contact0.exists())
        # Cannot add or edit contacts in fully synced lists
        with self.assertRaises(ValidationError):
            Contact.create({
                "list_id": self.list.id,
                "partner_id": self.partners[0].id,
            })
        contact1 = Contact.search([
            ("list_id", "=", self.list.id),
        ], limit=1)
        with self.assertRaises(ValidationError):
            contact1.name = "other"
        with self.assertRaises(ValidationError):
            contact1.email = "other@example.com"
        with self.assertRaises(ValidationError):
            contact1.partner_id = self.partners[0]

    def test_sync_when_sending_mail(self):
        """Dynamic list is synced before mailing to it."""
        self.list.action_sync()
        self.assertEqual(self.list.contact_nbr, 5)
        # Create a new partner
        self.partners.create({
            "name": "extra partner",
            "category_id": [(4, self.tag.id, False)],
            "email": "extra@example.com",
        })
        # Before sending the mail, the list is updated
        with patch("odoo.addons.base.ir.ir_mail_server"
                   ".IrMailServer.send_email") as send_email:
            self.mail.send_mail()
            self.assertEqual(6, send_email.call_count)
        self.assertEqual(6, self.list.contact_nbr)
