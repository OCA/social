# -*- coding: utf-8 -*-
# Copyright 2016 Tecnativa - Pedro M. Baeza
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo.tests import common
from odoo import exceptions
from ..hooks import pre_init_hook


class TestMassMailingUnique(common.SavepointCase):
    @classmethod
    def setUpClass(cls):
        super(TestMassMailingUnique, cls).setUpClass()
        cls.list = cls.env['mail.mass_mailing.list'].create({
            'name': 'Test list',
        })
        cls.contact1 = cls.env['mail.mass_mailing.contact'].create({
            'name': 'Contact 1',
            'email': 'email1@test.com',
        })

    def test_init_hook_list(self):
        # Disable temporarily the constraint
        self.env.cr.execute("""
            ALTER TABLE mail_mass_mailing_list
            DROP CONSTRAINT mail_mass_mailing_list_unique_name
            """)
        self.env['mail.mass_mailing.list'].create({
            'name': 'Test list',
        })
        with self.assertRaises(exceptions.ValidationError):
            pre_init_hook(self.env.cr)

    def test_init_hook_contact(self):
        # Disable temporarily the constraint
        self.env.cr.execute("""
            ALTER TABLE mail_mass_mailing_contact
            DROP CONSTRAINT mail_mass_mailing_contact_unique_mail_per_list
            """)
        self.env['mail.mass_mailing.contact'].create({
            'name': 'Contact 2',
            'email': 'email1@test.com',
        })
        with self.assertRaises(exceptions.ValidationError):
            pre_init_hook(self.env.cr)
