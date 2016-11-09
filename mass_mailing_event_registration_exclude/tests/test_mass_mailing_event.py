# -*- coding: utf-8 -*-
# Copyright 2016 Antonio Espinosa <antonio.espinosa@tecnativa.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from datetime import datetime, timedelta
from openerp.tests.common import TransactionCase


class TestMassMailingEvent(TransactionCase):
    def setUp(self, *args, **kwargs):
        super(TestMassMailingEvent, self).setUp(*args, **kwargs)

        day_1 = (datetime.now() + timedelta(days=1)).strftime(
            '%Y-%m-%d 8:00:00')
        day_2 = (datetime.now() + timedelta(days=5)).strftime(
            '%Y-%m-%d 18:00:00')
        self.event = self.env['event.event'].create({
            'name': 'Test event',
            'date_begin': day_1,
            'date_end': day_2,
        })
        self.registration = self.env['event.registration'].create({
            'event_id': self.event.id,
            'email': 'partner_a@example.org',
            'nb_register': 1,
            'state': 'draft',
        })
        self.states_all = self.env['event.registration.state'].search([])
        self.state_confirmed = self.env['event.registration.state'].search([
            ('code', '=', 'open'),
        ])

    def test_mailing_contact(self):
        contact_list = self.env['mail.mass_mailing.list'].create({
            'name': 'Test list',
        })
        contact_a = self.env['mail.mass_mailing.contact'].create({
            'list_id': contact_list.id,
            'name': 'Test contact A',
            'email': 'partner_a@example.org',
        })
        contact_b = self.env['mail.mass_mailing.contact'].create({
            'list_id': contact_list.id,
            'name': 'Test contact B',
            'email': 'partner_b@example.org',
        })
        domain = [
            ('list_id', 'in', [contact_list.id]),
            ('opt_out', '=', False),
        ]
        mass_mailing = self.env['mail.mass_mailing'].create({
            'name': 'Test subject',
            'email_from': 'from@example.com',
            'mailing_model': 'mail.mass_mailing.contact',
            'mailing_domain': str(domain),
            'contact_list_ids': [(6, False, [contact_list.id])],
            'body_html': '<p>Test email body</p>',
            'reply_to_mode': 'email',
        })
        m_contact = self.env['mail.mass_mailing.contact'].with_context(
            exclude_mass_mailing=mass_mailing.id)
        self.assertEqual(
            [contact_a.id, contact_b.id],
            mass_mailing.get_recipients(mass_mailing))
        self.assertEqual(2, m_contact.search_count(domain))
        mass_mailing.write({
            'event_id': self.event.id,
            'exclude_event_state_ids': [(6, False, self.states_all.ids)],
        })
        self.assertEqual(
            [contact_b.id],
            mass_mailing.get_recipients(mass_mailing))
        self.assertEqual(1, m_contact.search_count(domain))
        mass_mailing.write({
            'exclude_event_state_ids': [(6, False, self.state_confirmed.ids)],
        })
        self.assertEqual(
            [contact_a.id, contact_b.id],
            mass_mailing.get_recipients(mass_mailing))
        self.assertEqual(2, m_contact.search_count(domain))

    def test_mailing_partner(self):
        partner_a = self.env['res.partner'].create({
            'name': 'Test partner A',
            'email': 'partner_a@example.org',
        })
        partner_b = self.env['res.partner'].create({
            'name': 'Test partner B',
            'email': 'partner_b@example.org',
        })
        domain = [
            ('id', 'in', [partner_a.id, partner_b.id]),
            ('opt_out', '=', False),
        ]
        mass_mailing = self.env['mail.mass_mailing'].create({
            'name': 'Test subject',
            'email_from': 'from@example.com',
            'mailing_model': 'res.partner',
            'mailing_domain': str(domain),
            'body_html': '<p>Test email body</p>',
            'reply_to_mode': 'email',
        })
        m_partner = self.env['res.partner'].with_context(
            exclude_mass_mailing=mass_mailing.id)
        self.assertEqual(
            [partner_a.id, partner_b.id],
            mass_mailing.get_recipients(mass_mailing))
        self.assertEqual(2, m_partner.search_count(domain))
        mass_mailing.write({
            'event_id': self.event.id,
            'exclude_event_state_ids': [(6, False, self.states_all.ids)],
        })
        self.assertEqual(
            [partner_b.id],
            mass_mailing.get_recipients(mass_mailing))
        self.assertEqual(1, m_partner.search_count(domain))
        mass_mailing.write({
            'exclude_event_state_ids': [(6, False, self.state_confirmed.ids)],
        })
        self.assertEqual(
            [partner_a.id, partner_b.id],
            mass_mailing.get_recipients(mass_mailing))
        self.assertEqual(2, m_partner.search_count(domain))
