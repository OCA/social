# -*- coding: utf-8 -*-
# Copyright 2016 Antonio Espinosa - <antonio.espinosa@tecnativa.com>
# Copyright 2017 Vicent Cubells - <vicent.cubells@tecnativa.com>
# Copyright 2017 David Vidal - <david.vidal@tecnativa.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import mock
from odoo.tools import mute_logger
from odoo.tests.common import at_install, post_install, TransactionCase

mock_send_email = ('odoo.addons.base.ir.ir_mail_server.'
                   'IrMailServer.send_email')


@at_install(False)
@post_install(True)
class TestMassMailing(TransactionCase):
    def setUp(self, *args, **kwargs):
        super(TestMassMailing, self).setUp(*args, **kwargs)
        self.list = self.env['mail.mass_mailing.list'].create({
            'name': 'Test mail tracking',
        })
        self.list.name = '%s #%s' % (self.list.name, self.list.id)
        self.contact_a = self.env['mail.mass_mailing.contact'].create({
            'list_id': self.list.id,
            'name': 'Test contact A',
            'email': 'contact_a@example.com',
        })
        self.mailing = self.env['mail.mass_mailing'].create({
            'name': 'Test subject',
            'email_from': 'from@example.com',
            'mailing_model': 'mail.mass_mailing.contact',
            'mailing_domain': "[('list_id', 'in', [%d]), "
                              "('opt_out', '=', False)]" % self.list.id,
            'contact_list_ids': [(6, False, [self.list.id])],
            'body_html': '<p>Test email body</p>',
            'reply_to_mode': 'email',
        })

    @mute_logger('odoo.addons.mail.models.mail_mail')
    def test_smtp_error(self):
        with mock.patch(mock_send_email) as mock_func:
            mock_func.side_effect = Warning('Mock test error')
            self.mailing.send_mail()
            for stat in self.mailing.statistics_ids:
                if stat.mail_mail_id:
                    stat.mail_mail_id.send()
                tracking = self.env['mail.tracking.email'].search([
                    ('mail_id_int', '=', stat.mail_mail_id_int),
                ])
                for track in tracking:
                    self.assertEqual('error', track.state)
                    self.assertEqual('Warning', track.error_type)
                    self.assertEqual('Mock test error',
                                     track.error_description)
            self.assertTrue(self.contact_a.email_bounced)

    def test_tracking_email_link(self):
        self.mailing.send_mail()
        for stat in self.mailing.statistics_ids:
            if stat.mail_mail_id:
                stat.mail_mail_id.send()
            tracking_email = self.env['mail.tracking.email'].search([
                ('mail_id_int', '=', stat.mail_mail_id_int),
            ])
            self.assertTrue(tracking_email)
            self.assertEqual(
                tracking_email.mass_mailing_id.id, self.mailing.id)
            self.assertEqual(tracking_email.mail_stats_id.id, stat.id)
            self.assertEqual(stat.mail_tracking_id.id, tracking_email.id)
            # And now open the email
            metadata = {
                'ip': '127.0.0.1',
                'user_agent': 'Odoo Test/1.0',
                'os_family': 'linux',
                'ua_family': 'odoo',
            }
            tracking_email.event_create('open', metadata)
            self.assertTrue(stat.opened)

    def _tracking_email_bounce(self, event_type, state):
        self.mailing.send_mail()
        for stat in self.mailing.statistics_ids:
            if stat.mail_mail_id:
                stat.mail_mail_id.send()
            tracking_email = self.env['mail.tracking.email'].search([
                ('mail_id_int', '=', stat.mail_mail_id_int),
            ])
            # And now mark the email as bounce
            metadata = {
                'bounce_type': '499',
                'bounce_description': 'Unable to connect to MX servers',
            }
            tracking_email.event_create(event_type, metadata)
            self.assertTrue(stat.bounced)

    def test_tracking_email_hard_bounce(self):
        self._tracking_email_bounce('hard_bounce', 'bounced')

    def test_tracking_email_soft_bounce(self):
        self._tracking_email_bounce('soft_bounce', 'soft-bounced')

    def test_tracking_email_reject(self):
        self._tracking_email_bounce('reject', 'rejected')

    def test_tracking_email_spam(self):
        self._tracking_email_bounce('spam', 'spam')

    def test_contact_tracking_emails(self):
        self._tracking_email_bounce('hard_bounce', 'bounced')
        self.assertTrue(self.contact_a.email_bounced)
        self.assertTrue(self.contact_a.email_score < 50.0)
        self.contact_a.email = 'other_contact_a@example.com'
        self.assertFalse(self.contact_a.email_bounced)
        self.assertTrue(self.contact_a.email_score == 50.0)
        self.contact_a.email = 'contact_a@example.com'
        self.assertTrue(self.contact_a.email_bounced)
        self.assertTrue(self.contact_a.email_score < 50.0)
