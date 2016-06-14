# -*- coding: utf-8 -*-
# © 2016 Antonio Espinosa - <antonio.espinosa@tecnativa.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import mock
import base64
from openerp.tests.common import TransactionCase
from openerp.addons.mail_tracking.controllers.main import \
    MailTrackingController, BLANK

mock_request = 'openerp.http.request'
mock_send_email = ('openerp.addons.base.ir.ir_mail_server.'
                   'ir_mail_server.send_email')


class FakeUserAgent(object):
    browser = 'Test browser'
    platform = 'Test platform'

    def __str__(self):
        """Return name"""
        return 'Test suite'


# One test case per method
class TestMailTracking(TransactionCase):
    # Use case : Prepare some data for current test case
    def setUp(self):
        super(TestMailTracking, self).setUp()
        self.sender = self.env['res.partner'].create({
            'name': 'Test sender',
            'email': 'sender@example.com',
            'notify_email': 'always',
        })
        self.recipient = self.env['res.partner'].create({
            'name': 'Test recipient',
            'email': 'recipient@example.com',
            'notify_email': 'always',
        })
        self.request = {
            'httprequest': type('obj', (object,), {
                'remote_addr': '123.123.123.123',
                'user_agent': FakeUserAgent(),
            }),
        }

    def test_message_post(self):
        # This message will generate a notification for recipient
        message = self.env['mail.message'].create({
            'subject': 'Message test',
            'author_id': self.sender.id,
            'email_from': self.sender.email,
            'type': 'comment',
            'model': 'res.partner',
            'res_id': self.recipient.id,
            'partner_ids': [(4, self.recipient.id)],
            'body': '<p>This is a test message</p>',
        })
        # Search tracking created
        tracking_email = self.env['mail.tracking.email'].search([
            ('mail_message_id', '=', message.id),
            ('partner_id', '=', self.recipient.id),
        ])
        # The tracking email must be sent
        self.assertTrue(tracking_email)
        self.assertEqual(tracking_email.state, 'sent')
        # message_dict read by web interface
        message_dict = self.env['mail.message'].message_read(message.id)
        # First item is message content
        self.assertTrue(len(message_dict) > 0)
        message_dict = message_dict[0]
        self.assertTrue(len(message_dict['partner_ids']) > 0)
        # First partner is recipient
        partner_id = message_dict['partner_ids'][0][0]
        self.assertEqual(partner_id, self.recipient.id)
        status = message_dict['partner_trackings'][str(partner_id)]
        # Tracking status must be sent and
        # mail tracking must be the one search before
        self.assertEqual(status[0], 'sent')
        self.assertEqual(status[1], tracking_email.id)
        # And now open the email
        metadata = {
            'ip': '127.0.0.1',
            'user_agent': 'Odoo Test/1.0',
            'os_family': 'linux',
            'ua_family': 'odoo',
        }
        tracking_email.event_create('open', metadata)
        self.assertEqual(tracking_email.state, 'opened')

    def mail_send(self):
        mail = self.env['mail.mail'].create({
            'subject': 'Test subject',
            'email_from': 'from@domain.com',
            'email_to': 'to@domain.com',
            'body_html': '<p>This is a test message</p>',
        })
        mail.send()
        # Search tracking created
        tracking_email = self.env['mail.tracking.email'].search([
            ('mail_id', '=', mail.id),
        ])
        return mail, tracking_email

    def test_mail_send(self):
        controller = MailTrackingController()
        db = self.env.cr.dbname
        image = base64.decodestring(BLANK)
        mail, tracking = self.mail_send()
        self.assertEqual(mail.email_to, tracking.recipient)
        self.assertEqual(mail.email_from, tracking.sender)
        with mock.patch(mock_request) as mock_func:
            mock_func.return_value = type('obj', (object,), self.request)
            res = controller.mail_tracking_open(db, tracking.id)
            self.assertEqual(image, res.response[0])

    def test_smtp_error(self):
        with mock.patch(mock_send_email) as mock_func:
            mock_func.side_effect = Warning('Test error')
            mail, tracking = self.mail_send()
            self.assertEqual('error', tracking.state)
            self.assertEqual('Warning', tracking.error_type)
            self.assertEqual('Test error', tracking.error_description)

    def test_db(self):
        db = self.env.cr.dbname
        controller = MailTrackingController()
        with mock.patch(mock_request) as mock_func:
            mock_func.return_value = type('obj', (object,), self.request)
            not_found = controller.mail_tracking_all('not_found_db')
            self.assertEqual('NOT FOUND', not_found.response[0])
            none = controller.mail_tracking_all(db)
            self.assertEqual('NONE', none.response[0])
            none = controller.mail_tracking_event(db, 'open')
            self.assertEqual('NONE', none.response[0])
