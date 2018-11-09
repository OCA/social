# Copyright 2018 Tecnativa - Ernesto tejeda
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from . import base
from odoo.exceptions import ValidationError


class MailMassMailingListContactRelCase(base.BaseCase):

    def test_create_mass_mailing_list(self):
        contact_test_1 = self.create_mailing_contact({
            'name': 'Contact test 1',
            'partner_id': self.partner.id,
        })
        contact_test_2 = self.create_mailing_contact({
            'name': 'Contact test 2',
            'partner_id': self.partner.id,
        })
        list_3 = self.create_mailing_list({'name': 'List test 3'})

        self.env['mail.mass_mailing.list_contact_rel'].create({
            'list_id': list_3.id,
            'contact_id': contact_test_1.id,
        })

        with self.assertRaises(ValidationError):
            self.env['mail.mass_mailing.list_contact_rel'].create({
                'list_id': list_3.id,
                'contact_id': contact_test_2.id,
            })
