# -*- coding: utf-8 -*-
# © 2017 Phuc.nt - <phuc.nt@komit-consulting.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import logging

from mock import MagicMock
from odoo.tests.common import TransactionCase


class TestMailSplitByPartnerConf(TransactionCase):
    def setUp(self):
        super(TestMailSplitByPartnerConf, self).setUp()
        self.ICP = self.env['ir.config_parameter']
        self.recipient1 = self.env['res.partner'].create({
            'name': 'Test recipient 1',
            'email': 'recipient1@example.com',
            'notify_email': 'always',
        })
        self.recipient2 = self.env['res.partner'].create({
            'name': 'Test recipient 2',
            'email': 'recipient2@example.com',
            'notify_email': 'always',
        })

    def mail_send(self):
        send_mail = MagicMock()

        def mock_send_email(self, message, *args, **kwargs):
            message_id = message['Message-Id']
            if message['To']:
                logging.info('Test send email to <%s>', message['To'])
                send_mail()
            return message_id

        self.env['ir.mail_server']._patch_method('send_email', mock_send_email)

        mail = self.env['mail.mail'].create({
            'subject': 'Test mail',
            'email_from': 'from@domain.com',
            'email_to': 'to@domain.com',
            'body_html': '<p>This is a test message</p>',
            'recipient_ids':
                [(6, 0, [self.recipient1.id, self.recipient2.id])]
        })
        mail.send()
        return mail, send_mail.call_count

    def test_send_mail_merge_recipients(self):
        self.ICP.set_param('default_mail_split_by_partner_conf', 'merge')
        mail_sent_count = self.mail_send()[1]
        self.assertEqual(mail_sent_count, 1)

    def test_send_mail_split_recipients(self):
        self.ICP.set_param('default_mail_split_by_partner_conf', 'split')
        mail, mail_count = self.mail_send()
        count_recipients = len(mail.recipient_ids)
        if mail.email_to:
            count_recipients += 1
        self.assertEqual(mail_count, count_recipients)
