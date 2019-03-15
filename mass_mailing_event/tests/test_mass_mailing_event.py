# -*- coding: utf-8 -*-
# Copyright 2016 Antonio Espinosa <antonio.espinosa@tecnativa.com>
# Copyright 2017 David Vidal <david.vidal@tecnativa.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo.tests.common import at_install, post_install, SavepointCase


@at_install(True)
@post_install(True)
class TestMassMailingEvent(SavepointCase):

    @classmethod
    def setUpClass(cls):
        super(TestMassMailingEvent, cls).setUpClass()
        cls.event = cls.env['event.event'].create({
            'name': 'Test event',
            'date_begin': '2017-06-24 8:00:00',
            'date_end': '2017-06-30 18:00:00',
        })
        cls.registration = cls.env['event.registration'].create({
            'event_id': cls.event.id,
            'email': 'partner_a@example.org',
        })
        cls.states_all = cls.env['event.registration.state'].search([])
        cls.state_confirmed = cls.env['event.registration.state'].search([
            ('code', '=', 'open')
        ])
        cls.contact_list = cls.env['mail.mass_mailing.list'].create({
            'name': 'Test list',
        })
        cls.contact_a = cls.env['mail.mass_mailing.contact'].create({
            'list_id': cls.contact_list.id,
            'name': 'Test contact A',
            'email': 'partner_a@example.org',
        })
        cls.contact_b = cls.env['mail.mass_mailing.contact'].create({
            'list_id': cls.contact_list.id,
            'name': 'Test contact B',
            'email': 'partner_b@example.org',
        })
        cls.partner_a = cls.env['res.partner'].create({
            'name': 'Test partner A',
            'email': 'partner_a@example.org',
        })
        cls.partner_b = cls.env['res.partner'].create({
            'name': 'Test partner B',
            'email': 'partner_b@example.org',
        })

    def test_mailing_contact(self):
        domain = [
            ('list_id', 'in', [self.contact_list.id]),
            ('opt_out', '=', False),
        ]
        mass_mailing = self.env['mail.mass_mailing'].create({
            'name': 'Test subject',
            'email_from': 'from@example.com',
            'mailing_model': 'mail.mass_mailing.contact',
            'mailing_domain': str(domain),
            'contact_list_ids': [(6, 0, [self.contact_list.id])],
            'body_html': '<p>Test email body</p>',
            'reply_to_mode': 'email',
        })
        mail_contact = self.env['mail.mass_mailing.contact'].with_context(
            exclude_mass_mailing=mass_mailing.id)
        self.assertEqual(
            [self.contact_a.id, self.contact_b.id],
            mass_mailing.get_recipients())
        self.assertEqual(2, mail_contact.search_count(domain))
        mass_mailing.write({
            'event_id': self.event.id,
            'exclude_event_state_ids': [(6, 0, self.states_all.ids)],
        })
        self.assertEqual(
            [self.contact_b.id],
            mass_mailing.get_recipients())
        self.assertEqual(1, mail_contact.search_count(domain))
        self.registration.state = 'draft'
        mass_mailing.write({
            'exclude_event_state_ids': [(6, 0, self.state_confirmed.ids)],
        })
        self.assertEqual(
            [self.contact_a.id, self.contact_b.id],
            mass_mailing.get_recipients())
        self.assertEqual(2, mail_contact.search_count(domain))

    def test_mailing_partner(self):
        domain = [
            ('id', 'in', [self.partner_a.id, self.partner_b.id]),
            ('opt_out', '=', False),
        ]
        domain_reg = [
            ('event_id', '=', self.event.id),
        ]
        mass_mailing = self.env['mail.mass_mailing'].create({
            'name': 'Test subject',
            'email_from': 'from@example.com',
            'mailing_model': 'res.partner',
            'mailing_domain': str(domain),
            'body_html': '<p>Test email body</p>',
            'reply_to_mode': 'email',
        })
        mail_partner = self.env['res.partner'].with_context(
            exclude_mass_mailing=mass_mailing.id)
        mail_registration = self.env['event.registration'].with_context(
            exclude_mass_mailing=mass_mailing.id)
        self.assertEqual(
            [self.partner_a.id, self.partner_b.id],
            mass_mailing.get_recipients())
        self.assertEqual(2, mail_partner.search_count(domain))
        mass_mailing.write({
            'event_id': self.event.id,
            'exclude_event_state_ids': [(6, 0, self.states_all.ids)],
        })
        self.assertEqual(
            [self.partner_b.id],
            mass_mailing.get_recipients())
        self.assertEqual(1, mail_partner.search_count(domain))
        self.assertEqual(0, mail_registration.search_count(domain_reg))
        self.registration.state = 'draft'
        mass_mailing.write({
            'exclude_event_state_ids': [(6, 0, self.state_confirmed.ids)],
        })
        self.assertEqual(
            [self.partner_a.id, self.partner_b.id],
            mass_mailing.get_recipients())
        self.assertEqual(2, mail_partner.search_count(domain))
        self.assertEqual(1, mail_registration.search_count(domain_reg))
