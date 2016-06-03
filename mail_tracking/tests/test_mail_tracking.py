# -*- coding: utf-8 -*-
# © 2016 Antonio Espinosa - <antonio.espinosa@tecnativa.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from openerp.tests.common import TransactionCase


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
        tracking_email.event_process('open', metadata)
        self.assertEqual(tracking_email.state, 'opened')
