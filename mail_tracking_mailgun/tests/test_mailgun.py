# -*- coding: utf-8 -*-
# Copyright 2016 Antonio Espinosa - <antonio.espinosa@tecnativa.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from openerp.tests.common import TransactionCase


class TestMailgun(TransactionCase):
    def mail_send(self):
        mail = self.env['mail.mail'].create({
            'subject': 'Test subject',
            'email_from': 'from@example.com',
            'email_to': self.recipient,
            'body_html': '<p>This is a test message</p>',
        })
        mail.send()
        # Search tracking created
        tracking_email = self.env['mail.tracking.email'].search([
            ('mail_id', '=', mail.id),
        ])
        return mail, tracking_email

    def setUp(self):
        super(TestMailgun, self).setUp()
        self.recipient = u'to@example.com'
        self.mail, self.tracking_email = self.mail_send()
        self.api_key = u'key-12345678901234567890123456789012'
        self.token = u'f1349299097a51b9a7d886fcb5c2735b426ba200ada6e9e149'
        self.timestamp = u'1471021089'
        self.signature = ('4fb6d4dbbe10ce5d620265dcd7a3c0b8'
                          'ca0dede1433103891bc1ae4086e9d5b2')
        self.env['ir.config_parameter'].set_param(
            'mailgun.apikey', self.api_key)
        self.event = {
            'Message-Id': u'<xxx.xxx.xxx-openerp-xxx-res.partner@test_db>',
            'X-Mailgun-Sid': u'WyIwNjgxZSIsICJ0b0BleGFtcGxlLmNvbSIsICI3MG'
                             'I0MWYiXQ==',
            'token': self.token,
            'timestamp': self.timestamp,
            'signature': self.signature,
            'domain': u'example.com',
            'message-headers': u'[]',
            'recipient': self.recipient,
            'odoo_db': self.env.cr.dbname,
            'tracking_email_id': u'%s' % self.tracking_email.id
        }
        self.metadata = {
            'ip': '127.0.0.1',
            'user_agent': False,
            'os_family': False,
            'ua_family': False,
        }

    def event_search(self, event_type):
        event = self.env['mail.tracking.event'].search([
            ('tracking_email_id', '=', self.tracking_email.id),
            ('event_type', '=', event_type),
        ])
        self.assertTrue(event)
        return event

    def test_no_api_key(self):
        self.env['ir.config_parameter'].set_param('mailgun.apikey', '')
        self.test_event_delivered()

    def test_bad_signature(self):
        self.event.update({
            'event': u'delivered',
            'signature': u'bad_signature',
        })
        response = self.env['mail.tracking.email'].event_process(
            None, self.event, self.metadata)
        self.assertEqual('ERROR: Signature', response)

    def test_bad_event_type(self):
        self.event.update({
            'event': u'bad_event',
        })
        response = self.env['mail.tracking.email'].event_process(
            None, self.event, self.metadata)
        self.assertEqual('ERROR: Event type not supported', response)

    def test_bad_db(self):
        self.event.update({
            'event': u'delivered',
            'odoo_db': u'bad_db',
        })
        response = self.env['mail.tracking.email'].event_process(
            None, self.event, self.metadata)
        self.assertEqual('ERROR: Invalid DB', response)

    def test_bad_ts(self):
        timestamp = u'7a'  # Now time will be used instead
        signature = ('06cc05680f6e8110e59b41152b2d1c0f'
                     '1045d755ef2880ff922344325c89a6d4')
        self.event.update({
            'event': u'delivered',
            'timestamp': timestamp,
            'signature': signature,
        })
        response = self.env['mail.tracking.email'].event_process(
            None, self.event, self.metadata)
        self.assertEqual('OK', response)

    def test_tracking_not_found(self):
        self.event.update({
            'event': u'delivered',
            'tracking_email_id': u'bad_id',
        })
        response = self.env['mail.tracking.email'].event_process(
            None, self.event, self.metadata)
        self.assertEqual('ERROR: Tracking not found', response)

    # https://documentation.mailgun.com/user_manual.html#tracking-deliveries
    def test_event_delivered(self):
        self.event.update({
            'event': u'delivered',
        })
        response = self.env['mail.tracking.email'].event_process(
            None, self.event, self.metadata)
        self.assertEqual('OK', response)
        event = self.event_search('delivered')
        self.assertEqual(event.timestamp, float(self.timestamp))
        self.assertEqual(event.recipient, self.recipient)

    # https://documentation.mailgun.com/user_manual.html#tracking-opens
    def test_event_opened(self):
        ip = u'127.0.0.1'
        user_agent = u'Odoo Test/8.0 Gecko Firefox/11.0'
        os_family = u'Linux'
        ua_family = u'Firefox'
        ua_type = u'browser'
        self.event.update({
            'event': u'opened',
            'city': u'Mountain View',
            'country': u'US',
            'region': u'CA',
            'client-name': ua_family,
            'client-os': os_family,
            'client-type': ua_type,
            'device-type': u'desktop',
            'ip': ip,
            'user-agent': user_agent,
        })
        response = self.env['mail.tracking.email'].event_process(
            None, self.event, self.metadata)
        self.assertEqual('OK', response)
        event = self.event_search('open')
        self.assertEqual(event.timestamp, float(self.timestamp))
        self.assertEqual(event.recipient, self.recipient)
        self.assertEqual(event.ip, ip)
        self.assertEqual(event.user_agent, user_agent)
        self.assertEqual(event.os_family, os_family)
        self.assertEqual(event.ua_family, ua_family)
        self.assertEqual(event.ua_type, ua_type)
        self.assertEqual(event.mobile, False)
        self.assertEqual(event.user_country_id.code, 'US')

    # https://documentation.mailgun.com/user_manual.html#tracking-clicks
    def test_event_clicked(self):
        ip = u'127.0.0.1'
        user_agent = u'Odoo Test/8.0 Gecko Firefox/11.0'
        os_family = u'Linux'
        ua_family = u'Firefox'
        ua_type = u'browser'
        url = u'https://odoo-community.org'
        self.event.update({
            'event': u'clicked',
            'city': u'Mountain View',
            'country': u'US',
            'region': u'CA',
            'client-name': ua_family,
            'client-os': os_family,
            'client-type': ua_type,
            'device-type': u'tablet',
            'ip': ip,
            'user-agent': user_agent,
            'url': url,
        })
        response = self.env['mail.tracking.email'].event_process(
            None, self.event, self.metadata, event_type='click')
        self.assertEqual('OK', response)
        event = self.event_search('click')
        self.assertEqual(event.timestamp, float(self.timestamp))
        self.assertEqual(event.recipient, self.recipient)
        self.assertEqual(event.ip, ip)
        self.assertEqual(event.user_agent, user_agent)
        self.assertEqual(event.os_family, os_family)
        self.assertEqual(event.ua_family, ua_family)
        self.assertEqual(event.ua_type, ua_type)
        self.assertEqual(event.mobile, True)
        self.assertEqual(event.url, url)

    # https://documentation.mailgun.com/user_manual.html#tracking-unsubscribes
    def test_event_unsubscribed(self):
        ip = u'127.0.0.1'
        user_agent = u'Odoo Test/8.0 Gecko Firefox/11.0'
        os_family = u'Linux'
        ua_family = u'Firefox'
        ua_type = u'browser'
        self.event.update({
            'event': u'unsubscribed',
            'city': u'Mountain View',
            'country': u'US',
            'region': u'CA',
            'client-name': ua_family,
            'client-os': os_family,
            'client-type': ua_type,
            'device-type': u'mobile',
            'ip': ip,
            'user-agent': user_agent,
        })
        response = self.env['mail.tracking.email'].event_process(
            None, self.event, self.metadata)
        self.assertEqual('OK', response)
        event = self.event_search('unsub')
        self.assertEqual(event.timestamp, float(self.timestamp))
        self.assertEqual(event.recipient, self.recipient)
        self.assertEqual(event.ip, ip)
        self.assertEqual(event.user_agent, user_agent)
        self.assertEqual(event.os_family, os_family)
        self.assertEqual(event.ua_family, ua_family)
        self.assertEqual(event.ua_type, ua_type)
        self.assertEqual(event.mobile, True)

    # https://documentation.mailgun.com/
    #   user_manual.html#tracking-spam-complaints
    def test_event_complained(self):
        self.event.update({
            'event': u'complained',
        })
        response = self.env['mail.tracking.email'].event_process(
            None, self.event, self.metadata)
        self.assertEqual('OK', response)
        event = self.event_search('spam')
        self.assertEqual(event.timestamp, float(self.timestamp))
        self.assertEqual(event.recipient, self.recipient)
        self.assertEqual(event.error_type, 'spam')

    # https://documentation.mailgun.com/user_manual.html#tracking-bounces
    def test_event_bounced(self):
        code = u'550'
        error = (u"5.1.1 The email account does not exist.\n"
                 "5.1.1 double-checking the recipient's email address")
        notification = u"Please, check recipient's email address"
        self.event.update({
            'event': u'bounced',
            'code': code,
            'error': error,
            'notification': notification,
        })
        response = self.env['mail.tracking.email'].event_process(
            None, self.event, self.metadata)
        self.assertEqual('OK', response)
        event = self.event_search('hard_bounce')
        self.assertEqual(event.timestamp, float(self.timestamp))
        self.assertEqual(event.recipient, self.recipient)
        self.assertEqual(event.error_type, code)
        self.assertEqual(event.error_description, error)
        self.assertEqual(event.error_details, notification)

    # https://documentation.mailgun.com/user_manual.html#tracking-failures
    def test_event_dropped(self):
        reason = u'hardfail'
        code = u'605'
        description = u'Not delivering to previously bounced address'
        self.event.update({
            'event': u'dropped',
            'reason': reason,
            'code': code,
            'description': description,
        })
        response = self.env['mail.tracking.email'].event_process(
            None, self.event, self.metadata)
        self.assertEqual('OK', response)
        event = self.event_search('reject')
        self.assertEqual(event.timestamp, float(self.timestamp))
        self.assertEqual(event.recipient, self.recipient)
        self.assertEqual(event.error_type, reason)
        self.assertEqual(event.error_description, code)
        self.assertEqual(event.error_details, description)
