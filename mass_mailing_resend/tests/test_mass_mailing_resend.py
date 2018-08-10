# Copyright 2017-2018 Tecnativa - Pedro M. Baeza
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo.tests import common
from odoo import exceptions


class TestMassMailingResend(common.SavepointCase):
    @classmethod
    def setUpClass(cls):
        super(TestMassMailingResend, cls).setUpClass()
        cls.list = cls.env['mail.mass_mailing.list'].create({
            'name': 'Test list',
        })
        cls.contact1 = cls.env['mail.mass_mailing.contact'].create({
            'name': 'Contact 1',
            'email': 'email1@test.com',
        })
        cls.mass_mailing = cls.env['mail.mass_mailing'].create({
            'name': 'Test mass mailing',
            'email_from': 'test@example.org',
            'mailing_model_id': cls.env.ref(
                'mass_mailing.model_mail_mass_mailing_contact'
            ).id,
            'contact_list_ids': [(6, 0, cls.list.ids)],
            'reply_to_mode': 'thread',
        })

    def test_resend_error(self):
        with self.assertRaises(exceptions.UserError):
            self.mass_mailing.button_draft()

    def test_resend(self):
        self.mass_mailing.state = 'done'  # Force state
        self.assertEqual(self.mass_mailing.state, 'done')
        self.mass_mailing.button_draft()
        self.assertEqual(self.mass_mailing.state, 'draft')
