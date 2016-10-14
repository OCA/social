# -*- coding: utf-8 -*-
# Copyright 2016 Antonio Espinosa <antonio.espinosa@tecnativa.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from openerp.tests.common import TransactionCase
from openerp.exceptions import Warning as UserError


class TestMassMailingSending(TransactionCase):
    def setUp(self, *args, **kwargs):
        super(TestMassMailingSending, self).setUp(*args, **kwargs)

        self.list = self.env['mail.mass_mailing.list'].create({
            'name': 'Test list',
        })
        # Define a lower batch size for testing purposes
        self.env['ir.config_parameter'].set_param(
            'mail.mass_mailing.sending.batch_size', 5)
        self.contact_a = self.env['mail.mass_mailing.contact'].create({
            'list_id': self.list.id,
            'name': 'Test contact A',
            'email': 'contact_a@example.org',
        })
        self.contact_b = self.env['mail.mass_mailing.contact'].create({
            'list_id': self.list.id,
            'name': 'Test contact B',
            'email': 'contact_b@example.org',
        })
        for i in range(1, 6):
            self.env['mail.mass_mailing.contact'].create({
                'list_id': self.list.id,
                'name': 'Test contact %s' % i,
                'email': 'contact_%s@example.org' % i,
            })
        self.mass_mailing = self.env['mail.mass_mailing'].create({
            'name': 'Test mass mailing',
            'email_from': 'from@example.org',
            'mailing_model': 'mail.mass_mailing.contact',
            'mailing_domain': [
                ('list_id', 'in', [self.list.id]),
                ('opt_out', '=', False),
            ],
            'contact_list_ids': [(6, False, [self.list.id])],
            'body_html': '<p>Hello world!</p>',
            'reply_to_mode': 'email',
        })
        self.partner = self.env['res.partner'].create({
            'name': 'Test partner',
            'email': 'partner@example.org',
        })
        self.mass_mailing_short = self.env['mail.mass_mailing'].create({
            'name': 'Test mass mailing short',
            'email_from': 'from@example.org',
            'mailing_model': 'res.partner',
            'mailing_domain': [
                ('id', 'in', [self.partner.id]),
                ('opt_out', '=', False),
            ],
            'body_html': '<p>Hello partner!</p>',
            'reply_to_mode': 'email',
        })

    def test_cron_contacts(self):
        self.mass_mailing.with_context(sending_queue_enabled=True).send_mail()
        sendings = self.env['mail.mass_mailing.sending'].search([
            ('mass_mailing_id', '=', self.mass_mailing.id),
        ])
        stats = self.env['mail.mail.statistics'].search([
            ('mass_mailing_id', '=', self.mass_mailing.id),
        ])
        # Sending in 'enqueued' state and 0 email stats created
        self.assertEqual(1, len(sendings))
        self.assertEqual(0, len(stats))
        sending = sendings[0]
        self.assertEqual('enqueued', sending.state)
        self.assertEqual(7, sending.pending_count)
        self.assertEqual('sending', self.mass_mailing.state)
        self.assertEqual(7, self.mass_mailing.pending_count)
        # Create email stats
        sending.cron()
        stats = self.env['mail.mail.statistics'].search([
            ('mass_mailing_id', '=', self.mass_mailing.id),
        ])
        self.env.invalidate_all()
        # Sending in 'enqueued' state and 5 stats created, 2 pending, 5 sending
        self.assertEqual(5, len(stats))
        self.assertEqual('enqueued', sending.state)
        self.assertEqual(2, sending.pending_count)
        self.assertEqual(5, sending.sending_count)
        self.assertEqual('sending', self.mass_mailing.state)
        for stat in stats:
            if stat.mail_mail_id:
                stat.mail_mail_id.send()
        self.env.invalidate_all()
        # Check that 5 emails are already sent
        self.assertEqual(0, sending.sending_count)
        self.assertEqual(5, sending.sent_count)
        sending.cron()
        stats = self.env['mail.mail.statistics'].search([
            ('mass_mailing_id', '=', self.mass_mailing.id),
        ])
        self.env.invalidate_all()
        # Sending in 'sending' state and 7 stats created, 0 pending, 2 sending
        self.assertEqual(7, len(stats))
        self.assertEqual('sending', sending.state)
        self.assertEqual(0, sending.pending_count)
        self.assertEqual(2, sending.sending_count)
        self.assertEqual('sending', self.mass_mailing.state)
        for stat in stats:
            if stat.mail_mail_id:
                stat.mail_mail_id.send()
        self.env.invalidate_all()
        # Check that 7 emails are already sent
        self.assertEqual('sent', sending.state)
        self.assertEqual(0, sending.sending_count)
        self.assertEqual(7, sending.sent_count)
        self.assertEqual(0, sending.failed_count)
        self.assertEqual('done', self.mass_mailing.state)

    def test_cron_partners(self):
        self.mass_mailing_short.with_context(
            sending_queue_enabled=True).send_mail()
        sendings = self.env['mail.mass_mailing.sending'].search([
            ('mass_mailing_id', '=', self.mass_mailing_short.id),
        ])
        stats = self.env['mail.mail.statistics'].search([
            ('mass_mailing_id', '=', self.mass_mailing_short.id),
        ])
        # Sending in 'draft' state and 1 email stats created
        self.assertEqual(1, len(sendings))
        self.assertEqual(1, len(stats))
        sending = sendings[0]
        self.assertEqual('sending', sending.state)
        self.assertEqual(0, sending.pending_count)
        self.assertEqual('sending', self.mass_mailing_short.state)
        self.assertEqual(1, self.mass_mailing_short.pending_count)
        for stat in stats:
            if stat.mail_mail_id:
                stat.mail_mail_id.send()
        self.env.invalidate_all()
        # Check that 1 email are already sent
        self.assertEqual('sent', sending.state)
        self.assertEqual(0, sending.sending_count)
        self.assertEqual(1, sending.sent_count)
        self.assertEqual(0, sending.failed_count)
        self.assertEqual('done', self.mass_mailing_short.state)

    def test_concurrent(self):
        self.mass_mailing.with_context(sending_queue_enabled=True).send_mail()
        with self.assertRaises(UserError):
            self.mass_mailing.with_context(
                sending_queue_enabled=True).send_mail()

    def test_read_group(self):
        groups = self.env['mail.mass_mailing'].read_group(
            [('sent_date', '<', '1900-12-31')], ['state', 'name'], ['state'])
        self.assertTrue([
            x for x in groups if (
                x['state_count'] == 0 and x['state'][0] == 'sending')
        ])

    def test_no_recipients(self):
        empty_list = self.env['mail.mass_mailing.list'].create({
            'name': 'Test list with no recipients',
        })
        mass_mailing = self.env['mail.mass_mailing'].create({
            'name': 'Test mass mailing with no recipients',
            'email_from': 'from@example.org',
            'mailing_model': 'mail.mass_mailing.contact',
            'mailing_domain': [
                ('list_id', 'in', [empty_list.id]),
                ('opt_out', '=', False),
            ],
            'contact_list_ids': [(6, False, [empty_list.id])],
            'body_html': '<p>Hello no one!</p>',
            'reply_to_mode': 'email',
        })
        with self.assertRaises(UserError):
            mass_mailing.send_mail()
