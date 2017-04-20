# -*- coding: utf-8 -*-
# © 2017 Emanuel Cino - <ecino@compassion.ch>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
import mock
from openerp.tests.common import TransactionCase

mock_sendgrid_api_client = ('openerp.addons.mail_sendgrid.models.mail_mail'
                            '.SendGridAPIClient')
mock_config = ('openerp.addons.mail_sendgrid.models.mail_mail.'
               'config')


class FakeClient(object):
    """ Mock Sendgrid APIClient """
    status_code = 202
    body = 'ok'

    def __init__(self):
        self.client = self
        self.mail = self
        self.send = self

    def post(self, **kwargs):
        return self


class FakeRequest(object):
    """ Simulate a Sendgrid JSON request """
    def __init__(self, data):
        self.jsonrequest = [data]


class TestMailSendgrid(TransactionCase):
    def setUp(self):
        super(TestMailSendgrid, self).setUp()
        self.sendgrid_template = self.env['sendgrid.template'].create({
            'name': 'Test Template',
            'remote_id': 'a74795d7-f926-4bad-8e7a-ae95fabd70fc',
            'html_content': u'<h1>Test Sendgrid</h1><%body%>{footer}'
        })
        self.mail_template = self.env['mail.template'].create({
            'name': 'Test Template',
            'model_id': self.env.ref('base.model_res_partner').id,
            'subject': 'Test e-mail',
            'body_html': u'Dear ${object.name}, hello!',
            'sendgrid_template_ids': [
                (0, 0, {'lang': 'en_US', 'sendgrid_template_id':
                        self.sendgrid_template.id})]
        })
        self.recipient = self.env.ref('base.partner_demo')
        self.mass_mailing = self.env['mail.mass_mailing'].create({
            'email_from': 'admin@yourcompany.example.com',
            'name': 'Test Mass Mailing Sendgrid',
            'mailing_model': 'res.partner',
            'mailing_domain': "[('id', '=', %d)]" % self.recipient.id,
            'email_template_id': self.mail_template.id,
            'body_html': u'Dear ${object.name}, hello!',
            'reply_to_mode': 'thread',
        })
        self.timestamp = u'1471021089'
        self.event = {
            'timestamp': self.timestamp,
            'sg_event_id': u"f_JoKtrLQaOXUc4thXgROg",
            'email': self.recipient.email,
            'odoo_db': self.env.cr.dbname,
            'odoo_id': u'<xxx.xxx.xxx-openerp-xxx-res.partner@test_db>'
        }
        self.metadata = {
            'ip': '127.0.0.1',
            'user_agent': False,
            'os_family': False,
            'ua_family': False,
        }
        self.request = FakeRequest(self.event)

    @mock.patch(mock_sendgrid_api_client)
    @mock.patch(mock_config)
    def test_send_campaign(self, m_config, mock_sendgrid):
        """
        Test sending mass campaign with Sendgrid template
        and statistics update
        """
        self.env['ir.config_parameter'].set_param(
            'mail_sendgrid.send_method', 'sendgrid')
        mock_sendgrid.return_value = FakeClient()
        m_config.get.return_value = 'we4iorujeriu'
        emails = self.mass_mailing.send_mail()
        self.assertEqual(len(emails), 1)
        self.assertEqual(emails.state, 'outgoing')
        self.assertEqual(emails.sendgrid_template_id.id,
                         self.sendgrid_template.id)

        emails.send()
        self.assertTrue(mock_sendgrid.called)
        self.assertEqual(emails.state, 'sent')
        mail_tracking = emails.tracking_email_ids
        self.assertEqual(len(mail_tracking), 1)
        self.assertFalse(mail_tracking.state)
        stats = self.mass_mailing.statistics_ids
        self.assertEqual(len(stats), 1)
        self.assertFalse(stats.sent)

        # Test delivered
        self.event.update({
            'event': 'delivered',
            'odoo_id': emails.message_id
        })
        self.env['mail.tracking.email'].event_process(
            self.request, self.event, self.metadata)
        self.assertTrue(stats.sent)

        # Test click e-mail
        self.event.update({
            'event': 'click',
        })
        self.env['mail.tracking.email'].event_process(
            self.request, self.event, self.metadata)
        self.assertEqual(emails.click_count, 1)
        events = stats.tracking_event_ids
        self.assertEqual(len(events), 2)
        self.assertEqual(events[0].event_type, 'delivered')
        self.assertEqual(events[1].event_type, 'click')
        self.assertEqual(stats.state, 'sent')
