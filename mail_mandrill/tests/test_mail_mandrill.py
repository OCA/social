# -*- coding: utf-8 -*-
# License AGPL-3: Antiun Ingenieria S.L. - Antonio Espinosa
# See README.rst file on addon root folder for more details

import json
from openerp.tests.common import TransactionCase
from openerp.tools.safe_eval import safe_eval


class TestMailMandrill(TransactionCase):
    def setUp(self):
        super(TestMailMandrill, self).setUp()
        message_obj = self.env['mail.mandrill.message']
        self.partner_01 = self.env.ref('base.res_partner_1')
        self.partner_02 = self.env.ref('base.res_partner_2')
        self.model = 'res.partner'
        self.res_id = self.partner_02.id
        self.mandrill_message_id = '0123456789abcdef0123456789abcdef'
        self.event_deferral = {
            'msg': {
                'sender': 'username01@example.com',
                'tags': [],
                'smtp_events': [
                    {
                        'destination_ip': '123.123.123.123',
                        'diag': 'Event description',
                        'source_ip': '145.145.145.145',
                        'ts': 1455192896,
                        'type': 'deferred',
                        'size': 19513
                    },
                ],
                'ts': 1455008558,
                'clicks': [],
                'resends': [],
                'state': 'deferred',
                '_version': '1abcdefghijkABCDEFGHIJ',
                'template': None,
                '_id': self.mandrill_message_id,
                'email': 'username02@example.com',
                'metadata': {
                    'odoo_id': self.res_id,
                    'odoo_db': 'test',
                    'odoo_model': self.model,
                },
                'opens': [],
                'subject': 'My favorite subject'
            },
            'diag': '454 4.7.1 <username02@example.com>: Relay access denied',
            '_id': self.mandrill_message_id,
            'event': 'deferral',
            'ts': 1455201028,
        }
        self.event_send = {
            'msg': {
                '_id': self.mandrill_message_id,
                'subaccount': None,
                'tags': [],
                'smtp_events': [],
                'ts': 1455201157,
                'email': 'username02@example.com',
                'metadata': {
                    'odoo_id': self.res_id,
                    'odoo_db': 'test',
                    'odoo_model': self.model,
                },
                'state': 'sent',
                'sender': 'username01@example.com',
                'template': None,
                'reject': None,
                'resends': [],
                'clicks': [],
                'opens': [],
                'subject': 'My favorite subject',
            },
            '_id': self.mandrill_message_id,
            'event': 'send',
            'ts': 1455201159,
        }
        self.event_hard_bounce = {
            'msg': {
                'bounce_description': 'bad_mailbox',
                'sender': 'username01@example.com',
                'tags': [],
                'diag': 'smtp;550 5.4.1 [username02@example.com]: '
                        'Recipient address rejected: Access denied',
                'smtp_events': [],
                'ts': 1455194565,
                'template': None,
                '_version': 'abcdefghi123456ABCDEFG',
                'metadata': {
                    'odoo_id': self.res_id,
                    'odoo_db': 'test',
                    'odoo_model': self.model,
                },
                'resends': [],
                'state': 'bounced',
                'bgtools_code': 10,
                '_id': self.mandrill_message_id,
                'email': 'username02@example.com',
                'subject': 'My favorite subject',
            },
            '_id': self.mandrill_message_id,
            'event': 'hard_bounce',
            'ts': 1455195340
        }
        self.event_soft_bounce = {
            'msg': {
                'bounce_description': 'general',
                'sender': 'username01@example.com',
                'tags': [],
                'diag': 'X-Notes; Error transferring to FQDN.EXAMPLE.COM\n ; '
                        'SMTP Protocol Returned a Permanent Error 550 5.7.1 '
                        'Unable to relay\n\n--==ABCDEFGHIJK12345678ABCDEFGH',
                'smtp_events': [],
                'ts': 1455194562,
                'template': None,
                '_version': 'abcdefghi123456ABCDEFG',
                'metadata': {
                    'odoo_id': self.res_id,
                    'odoo_db': 'test',
                    'odoo_model': self.model,
                },
                'resends': [],
                'state': 'soft-bounced',
                'bgtools_code': 40,
                '_id': self.mandrill_message_id,
                'email': 'username02@example.com',
                'subject': 'My favorite subject',
            },
            '_id': self.mandrill_message_id,
            'event': 'soft_bounce',
            'ts': 1455195622
        }
        self.event_open = {
            'ip': '111.111.111.111',
            'ts': 1455189075,
            'location': {
                'country_short': 'PT',
                'city': 'Porto',
                'country': 'Portugal',
                'region': 'Porto',
                'longitude': -8.61098957062,
                'postal_code': '-',
                'latitude': 41.1496086121,
                'timezone': '+01:00',
            },
            'msg': {
                'sender': 'username01@example.com',
                'tags': [],
                'smtp_events': [
                    {
                        'destination_ip': '222.222.222.222',
                        'diag': '250 2.0.0 ABCDEFGHIJK123456ABCDE mail '
                                'accepted for delivery',
                        'source_ip': '111.1.1.1',
                        'ts': 1455185877,
                        'type': 'sent',
                        'size': 30276,
                    },
                ],
                'ts': 1455185876,
                'clicks': [],
                'metadata': {
                    'odoo_id': self.res_id,
                    'odoo_db': 'test',
                    'odoo_model': self.model,
                },
                'resends': [],
                'state': 'sent',
                '_version': 'abcdefghi123456ABCDEFG',
                'template': None,
                '_id': self.mandrill_message_id,
                'email': 'username02@example.com',
                'opens': [
                    {
                        'ip': '111.111.111.111',
                        'ua': 'Windows/Windows 7/Outlook 2010/Outlook 2010',
                        'ts': 1455186247,
                        'location':
                        'Porto, PT'
                    }, {
                        'ip': '111.111.111.111',
                        'ua': 'Windows/Windows 7/Outlook 2010/Outlook 2010',
                        'ts': 1455189075,
                        'location': 'Porto, PT'
                    },
                ],
                'subject': 'My favorite subject',
            },
            '_id': self.mandrill_message_id,
            'user_agent_parsed': {
                'ua_name': 'Outlook 2010',
                'mobile': False,
                'ua_company_url': 'http://www.microsoft.com/',
                'os_icon': 'http://cdn.mandrill.com/img/email-client-icons/'
                           'windows-7.png',
                'os_company': 'Microsoft Corporation.',
                'ua_version': None,
                'os_name': 'Windows 7',
                'ua_family': 'Outlook 2010',
                'os_url': 'http://en.wikipedia.org/wiki/Windows_7',
                'os_company_url': 'http://www.microsoft.com/',
                'ua_company': 'Microsoft Corporation.',
                'os_family': 'Windows',
                'type': 'Email Client',
                'ua_icon': 'http://cdn.mandrill.com/img/email-client-icons/'
                           'outlook-2010.png',
                'ua_url': 'http://en.wikipedia.org/wiki/Microsoft_Outlook',
            },
            'event': 'open',
            'user_agent': 'Mozilla/4.0 (compatible; MSIE 7.0; Windows NT 6.1; '
                          'Trident/7.0; SLCC2; .NET CLR 2.0.50727; '
                          '.NET CLR 3.5.30729; .NET CLR 3.0.30729; '
                          'Media Center PC 6.0; .NET4.0C; .NET4.0E; BRI/2; '
                          'Tablet PC 2.0; GWX:DOWNLOADED; '
                          'Microsoft Outlook 14.0.7166; ms-office; '
                          'MSOffice 14)',
        }
        self.event_click = {
            'url': 'http://www.example.com/index.php',
            'ip': '111.111.111.111',
            'ts': 1455186402,
            'user_agent': 'Mozilla/5.0 (Windows NT 6.1) '
                          'AppleWebKit/537.36 (KHTML, like Gecko) '
                          'Chrome/48.0.2564.103 Safari/537.36',
            'msg': {
                'sender': 'username01@example.com',
                'tags': [],
                'smtp_events': [
                    {
                        'destination_ip': '222.222.222.222',
                        'diag': '250 2.0.0 Ok: queued as 12345678',
                        'source_ip': '111.1.1.1',
                        'ts': 1455186065,
                        'type': 'sent',
                        'size': 30994,
                    },
                ],
                'ts': 1455186063,
                'clicks': [
                    {
                        'url': 'http://www.example.com/index.php',
                        'ip': '111.111.111.111',
                        'ua': 'Windows/Windows 7/Chrome/Chrome 48.0.2564.103',
                        'ts': 1455186402,
                        'location': 'Madrid, ES',
                    },
                ],
                'metadata': {
                    'odoo_id': self.res_id,
                    'odoo_db': 'test',
                    'odoo_model': self.model,
                },
                'resends': [],
                'state': 'sent',
                '_version': 'abcdefghi123456ABCDEFG',
                'template': None,
                '_id': self.mandrill_message_id,
                'email': 'username02@example.com',
                'opens': [
                    {
                        'ip': '111.111.111.111',
                        'ua': 'Windows/Windows 7/Chrome/Chrome 48.0.2564.103',
                        'ts': 1455186402,
                        'location': 'Madrid, ES',
                    },
                ],
                'subject': 'My favorite subject',
            },
            '_id': self.mandrill_message_id,
            'user_agent_parsed': {
                'ua_name': 'Chrome 48.0.2564.103',
                'mobile': False,
                'ua_company_url': 'http://www.google.com/',
                'os_icon': 'http://cdn.mandrill.com/img/email-client-icons/'
                           'windows-7.png',
                'os_company': 'Microsoft Corporation.',
                'ua_version': '48.0.2564.103',
                'os_name': 'Windows 7',
                'ua_family': 'Chrome',
                'os_url': 'http://en.wikipedia.org/wiki/Windows_7',
                'os_company_url': 'http://www.microsoft.com/',
                'ua_company': 'Google Inc.',
                'os_family': 'Windows',
                'type': 'Browser',
                'ua_icon': 'http://cdn.mandrill.com/img/email-client-icons/'
                           'chrome.png',
                'ua_url': 'http://www.google.com/chrome',
            },
            'event': 'click',
            'location': {
                'country_short': 'ES',
                'city': 'Madrid',
                'country': 'Spain',
                'region': 'Madrid',
                'longitude': -3.70255994797,
                'postal_code': '-',
                'latitude': 40.4165000916,
                'timezone': '+02:00',
            },
        }
        self.event_spam = {
            'msg': {
                'sender': 'username01@example.com',
                'tags': [],
                'smtp_events': [],
                'ts': 1455186007,
                'clicks': [],
                'metadata': {
                    'odoo_id': self.res_id,
                    'odoo_db': 'test',
                    'odoo_model': self.model,
                },
                'resends': [],
                'state': 'spam',
                '_version': 'abcdefghi123456ABCDEFG',
                'template': None,
                '_id': self.mandrill_message_id,
                'email': 'username02@example.com',
                'opens': [],
                'subject': 'My favorite subject',
            },
            '_id': self.mandrill_message_id,
            'event': 'spam',
            'ts': 1455186366
        }
        self.event_reject = {
            'msg': {
                '_id': self.mandrill_message_id,
                'subaccount': None,
                'tags': [],
                'smtp_events': [],
                'ts': 1455194291,
                'email': 'username02@example.com',
                'metadata': {
                    'odoo_id': self.res_id,
                    'odoo_db': 'test',
                    'odoo_model': self.model,
                },
                'state': 'rejected',
                'sender': 'username01@example.com',
                'template': None,
                'reject': None,
                'resends': [],
                'clicks': [],
                'opens': [],
                'subject': 'My favorite subject',
            },
            '_id': self.mandrill_message_id,
            'event': 'reject',
            'ts': 1455194291,
        }
        self.event_unsub = {
            'msg': {
                '_id': self.mandrill_message_id,
                'subaccount': None,
                'tags': [],
                'smtp_events': [],
                'ts': 1455194291,
                'email': 'username02@example.com',
                'metadata': {
                    'odoo_id': self.res_id,
                    'odoo_db': 'test',
                    'odoo_model': self.model,
                },
                'state': 'unsub',
                'sender': 'username01@example.com',
                'template': None,
                'reject': None,
                'resends': [],
                'clicks': [],
                'opens': [],
                'subject': 'My favorite subject',
            },
            '_id': self.mandrill_message_id,
            'event': 'unsub',
            'ts': 1455194291,
        }
        self.message = message_obj.create(
            message_obj._message_prepare(
                self.mandrill_message_id, 'deferral', self.event_deferral))

    # Test Unit: mail_mail.py
    def test_mandrill_headers_add(self):
        mail_obj = self.env['mail.mail']
        message = self.env['mail.message'].create({
            'author_id': self.partner_01.id,
            'subject': 'Test subject',
            'body': 'Test body',
            'partner_ids': [(4, self.partner_02.id)],
            'model': self.model,
            'res_id': self.res_id,
        })
        mail = mail_obj.create({
            'mail_message_id': message.id,
        })
        mail._mandrill_headers_add()
        headers = safe_eval(mail.headers)
        self.assertIn('X-MC-Metadata', headers)
        metadata = json.loads(headers.get('X-MC-Metadata', '[]'))
        self.assertIn('odoo_db', metadata)
        self.assertIn('odoo_model', metadata)
        self.assertIn('odoo_id', metadata)
        self.assertEqual(metadata['odoo_model'], self.model)
        self.assertEqual(metadata['odoo_id'], self.res_id)

    # Test Unit: mail_mandrill_message.py
    def test_message_prepare(self):
        data = self.env['mail.mandrill.message']._message_prepare(
            self.mandrill_message_id, 'deferral', self.event_deferral)
        self.assertEqual(data['mandrill_id'], self.mandrill_message_id)
        self.assertEqual(data['timestamp'],
                         self.event_deferral['msg']['ts'])
        self.assertEqual(data['recipient'],
                         self.event_deferral['msg']['email'])
        self.assertEqual(data['sender'],
                         self.event_deferral['msg']['sender'])
        self.assertEqual(data['name'],
                         self.event_deferral['msg']['subject'])

    def test_event_prepare(self):
        data = self.env['mail.mandrill.message']._event_prepare(
            self.message, 'deferral', self.event_deferral)
        self.assertEqual(self.message.state, 'deferred')
        self.assertEqual(data['message_id'], self.message.id)
        self.assertEqual(data['event_type'], 'deferral')
        self.assertEqual(data['timestamp'], self.event_deferral['ts'])

    def test_process(self):
        event = self.env['mail.mandrill.message'].process(
            self.mandrill_message_id, 'deferral', self.event_deferral)
        self.assertEqual(event.message_id.mandrill_id,
                         self.mandrill_message_id)
        self.assertEqual(event.message_id.state, 'deferred')
        self.assertEqual(event.event_type, 'deferral')
        self.assertEqual(event.timestamp, self.event_deferral['ts'])

    # Test Unit: mail_mandrill_event.py
    def test_process_send(self):
        data = self.env['mail.mandrill.event'].process_send(
            self.message, self.event_send)
        self.assertEqual(self.message.state, 'sent')
        self.assertEqual(data['message_id'], self.message.id)
        self.assertEqual(data['event_type'], 'send')
        self.assertEqual(data['timestamp'], self.event_send['ts'])

    def test_process_deferral(self):
        data = self.env['mail.mandrill.event'].process_deferral(
            self.message, self.event_deferral)
        self.assertEqual(self.message.state, 'deferred')
        self.assertEqual(data['message_id'], self.message.id)
        self.assertEqual(data['event_type'], 'deferral')
        self.assertEqual(data['timestamp'], self.event_deferral['ts'])

    def test_process_hard_bounce(self):
        data = self.env['mail.mandrill.event'].process_hard_bounce(
            self.message, self.event_hard_bounce)
        self.assertEqual(self.message.state, 'bounced')
        self.assertEqual(self.message.bounce_type,
                         self.event_hard_bounce['msg']['bounce_description'])
        self.assertEqual(self.message.bounce_description,
                         self.event_hard_bounce['msg']['diag'])
        self.assertEqual(data['message_id'], self.message.id)
        self.assertEqual(data['event_type'], 'hard_bounce')
        self.assertEqual(data['timestamp'], self.event_hard_bounce['ts'])

    def test_process_soft_bounce(self):
        data = self.env['mail.mandrill.event'].process_soft_bounce(
            self.message, self.event_soft_bounce)
        self.assertEqual(self.message.state, 'bounced')
        self.assertEqual(self.message.bounce_type,
                         self.event_soft_bounce['msg']['bounce_description'])
        self.assertEqual(self.message.bounce_description,
                         self.event_soft_bounce['msg']['diag'])
        self.assertEqual(data['message_id'], self.message.id)
        self.assertEqual(data['event_type'], 'soft_bounce')
        self.assertEqual(data['timestamp'], self.event_soft_bounce['ts'])

    def test_process_open(self):
        data = self.env['mail.mandrill.event'].process_open(
            self.message, self.event_open)
        self.assertEqual(self.message.state, 'opened')
        self.assertEqual(data['message_id'], self.message.id)
        self.assertEqual(data['event_type'], 'open')
        self.assertEqual(data['timestamp'], self.event_open['ts'])
        self.assertEqual(data['ip'], self.event_open['ip'])

    def test_process_click(self):
        data = self.env['mail.mandrill.event'].process_click(
            self.message, self.event_open)
        self.assertEqual(self.message.state, 'opened')
        self.assertEqual(data['message_id'], self.message.id)
        self.assertEqual(data['event_type'], 'click')
        self.assertEqual(data['timestamp'], self.event_open['ts'])
        self.assertEqual(data['ip'], self.event_open['ip'])

    def test_process_spam(self):
        data = self.env['mail.mandrill.event'].process_spam(
            self.message, self.event_spam)
        self.assertEqual(self.message.state, 'spam')
        self.assertEqual(data['message_id'], self.message.id)
        self.assertEqual(data['event_type'], 'spam')
        self.assertEqual(data['timestamp'], self.event_spam['ts'])

    def test_process_reject(self):
        data = self.env['mail.mandrill.event'].process_reject(
            self.message, self.event_reject)
        self.assertEqual(self.message.state, 'rejected')
        self.assertEqual(data['message_id'], self.message.id)
        self.assertEqual(data['event_type'], 'reject')
        self.assertEqual(data['timestamp'], self.event_reject['ts'])

    def test_process_unsub(self):
        data = self.env['mail.mandrill.event'].process_unsub(
            self.message, self.event_unsub)
        self.assertEqual(self.message.state, 'unsub')
        self.assertEqual(data['message_id'], self.message.id)
        self.assertEqual(data['event_type'], 'unsub')
        self.assertEqual(data['timestamp'], self.event_unsub['ts'])
