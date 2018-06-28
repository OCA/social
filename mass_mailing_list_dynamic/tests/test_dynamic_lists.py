# -*- coding: utf-8 -*-
# Copyright 2017 Tecnativa - Jairo Llopis
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from mock import patch
from odoo.exceptions import ValidationError
from odoo.tests import common


@common.at_install(False)
@common.post_install(True)
class DynamicListCase(common.SavepointCase):
    @classmethod
    def setUpClass(cls):
        super(DynamicListCase, cls).setUpClass()
        cls.tag = cls.env["res.partner.category"].create({
            "name": "testing tag",
        })
        cls.partners = cls.env["res.partner"]
        for number in range(5):
            cls.partners |= cls.partners.create({
                "name": "partner %d" % number,
                "category_id": [(4, cls.tag.id, False)],
                "email": "%d@example.com" % number,
            })
        cls.list = cls.env["mail.mass_mailing.list"].create({
            "name": "test list",
            "dynamic": True,
            "sync_domain": repr([("category_id", "in", cls.tag.ids)]),
        })
        cls.mail = cls.env["mail.mass_mailing"].create({
            "name": "test mass mailing",
            "contact_list_ids": [(4, cls.list.id, False)],
        })
        cls.mail._onchange_model_and_list()

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
        Contact.search([
            ("list_id", "=", self.list.id),
            ("partner_id", "=", self.partners[2].id),
        ]).unlink()
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
        # Unset dynamic list
        self.list.dynamic = False
        # Now the contact is created without exception
        Contact.create({
            "list_id": self.list.id,
            "email": "test@example.com",
        })
        # Contacts can now be changed
        contact1.name = "other"

    def test_sync_when_sending_mail(self):
        """Check that list in synced when sending a mass mailing."""
        self.list.action_sync()
        self.assertEqual(self.list.contact_nbr, 5)
        # Create a new partner
        self.partners.create({
            "name": "extra partner",
            "category_id": [(4, self.tag.id, False)],
            "email": "extra@example.com",
        })
        # Mock sending low level method, because an auto-commit happens there
        with patch("odoo.addons.mail.models.mail_mail.MailMail.send") as s:
            self.mail.send_mail()
            self.assertEqual(1, s.call_count)
        self.assertEqual(6, self.list.contact_nbr)

    def test_load_filter(self):
        domain = "[('id', '=', 1)]"
        ir_filter = self.env['ir.filters'].create({
            'name': 'Test filter',
            'model_id': 'res.partner',
            'domain': domain,
        })
        wizard = self.env['mail.mass_mailing.load.filter'].with_context(
            active_id=self.list.id,
        ).create({
            'filter_id': ir_filter.id,
        })
        wizard.load_filter()
        self.assertEqual(self.list.sync_domain, domain)

    def test_change_partner(self):
        self.list.sync_method = 'full'
        self.list.action_sync()
        # This shouldn't fail
        self.partners[:1].write({
            'email': 'test_mass_mailing_list_dynamic@example.org',
        })
