# -*- coding: utf-8 -*-
# License AGPL-3: Antiun Ingenieria S.L. - Javier Iniesta
# See README.rst file on addon root folder for more details

from openerp.tests.common import TransactionCase


class TestEventRegistrationMailListWizard(TransactionCase):

    def setUp(self):
        super(TestEventRegistrationMailListWizard, self).setUp()
        self.mail_list = self.env['mail.mass_mailing.list'].create({
            'name': 'Test 01'})
        self.contact = self.env['mail.mass_mailing.contact'].create({
            'name': 'Test Contact 01', 'email': 'email01@test.com',
            'list_id': self.mail_list.id})
        self.event = self.env.ref('event.event_0')
        self.registration_01 = self.env['event.registration'].create({
            'name': 'Test Registration 01', 'email': 'email01@test.com',
            'event_id': self.event.id})
        self.registration_02 = self.env['event.registration'].create({
            'name': 'Test Registration 02', 'email': 'email02@test.com',
            'event_id': self.event.id})

    def test_add_to_mail_list(self):
        wizard = self.env['event.registration.mail.list.wizard'].create({
            'mail_list': self.mail_list.id})
        wizard.with_context(
            {'active_ids': [self.registration_01.id,
                            self.registration_02.id]}).add_to_mail_list()

        self.assertEqual(self.mail_list.contact_nbr, 2)
