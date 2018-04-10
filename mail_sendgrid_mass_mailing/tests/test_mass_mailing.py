# -*- coding: utf-8 -*-
# © 2017 Emanuel Cino - <ecino@compassion.ch>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
import mock
from odoo.tests.common import SavepointCase

mock_sendgrid_api_client = ('odoo.addons.mail_sendgrid.models.mail_mail'
                            '.SendGridAPIClient')
mock_config = ('odoo.addons.mail_sendgrid.models.mail_mail.'
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


class TestMailSendgrid(SavepointCase):

    @classmethod
    def setUpClass(cls):
        super(TestMailSendgrid, cls).setUpClass()
        cls.sendgrid_template = cls.env['sendgrid.template'].create({
            'name': 'Test Template',
            'remote_id': 'a74795d7-f926-4bad-8e7a-ae95fabd70fc',
            'html_content': u'<h1>Test Sendgrid</h1><%body%>{footer}'
        })
        cls.mail_template = cls.env['mail.template'].create({
            'name': 'Test Template',
            'model_id': cls.env.ref('base.model_res_partner').id,
            'subject': 'Test e-mail',
            'body_html': u'Dear ${object.name}, hello!',
            'sendgrid_template_ids': [
                (0, 0, {'lang': 'en_US', 'sendgrid_template_id':
                        cls.sendgrid_template.id})]
        })
        cls.recipient = cls.env.ref('base.partner_demo')
        cls.mass_mailing = cls.env['mail.mass_mailing'].create({
            'email_from': 'admin@yourcompany.example.com',
            'name': 'Test Mass Mailing Sendgrid',
            'mailing_model': 'res.partner',
            'mailing_domain': "[('id', '=', %d)]" % cls.recipient.id,
            'email_template_id': cls.mail_template.id,
            'body_html': u'Dear ${object.name}, hello!',
            'reply_to_mode': 'email',
            'enable_unsubscribe': True,
            'unsubscribe_tag': '[unsub]'
        }).with_context(lang='en_US', test_mode=True)
        cls.timestamp = u'1471021089'
        cls.event = {
            'timestamp': cls.timestamp,
            'sg_event_id': u"f_JoKtrLQaOXUc4thXgROg",
            'email': cls.recipient.email,
            'odoo_db': cls.env.cr.dbname,
            'odoo_id': u'<xxx.xxx.xxx-openerp-xxx-res.partner@test_db>'
        }
        cls.metadata = {
            'ip': '127.0.0.1',
            'user_agent': False,
            'os_family': False,
            'ua_family': False,
        }
        cls.request = FakeRequest(cls.event)

    def test_sendgrid_preview(self):
        """
        Test the preview field is getting the Sendgrid template
        """
        self.mass_mailing.html_copy = self.mass_mailing.body_html
        preview = self.mass_mailing.body_sendgrid
        self.assertIn(u'<h1>Test Sendgrid</h1>', preview)
        self.assertIn('hello!', preview)

    def test_change_language(self):
        """
        Test changing the language is changing the domain
        """
        domain = self.mass_mailing.mailing_domain
        self.mass_mailing.lang = self.env['res.lang'].search([], limit=1)
        self.mass_mailing.onchange_lang()
        self.assertTrue(len(self.mass_mailing.mailing_domain) > len(domain))

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

        # Test campaign
        self.mass_mailing.action_test_mailing()
        self.env['mail.mass_mailing.test'].create({
            'mass_mailing_id': self.mass_mailing.id,
            'email_to': 'test@sendgrid.com'
        }).with_context(lang='en_US', test_mode=True).send_mail_test()
        self.assertTrue(mock_sendgrid.called)
        mock_sendgrid.reset_mock()

        # Send campaign
        emails = self.mass_mailing.send_mail()
        # Dont delete emails sent
        emails.write({'auto_delete': False})
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
        self.assertTrue(stats.sent)

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
        self.assertIn('delivered', events.mapped('event_type'))
        self.assertIn('click', events.mapped('event_type'))
        self.assertEqual(stats.state, 'sent')

        # Test reject
        self.event.update({
            'event': 'dropped',
        })
        self.env['mail.tracking.email'].event_process(
            self.request, self.event, self.metadata)
        self.assertEqual(stats.state, 'exception')

    @classmethod
    def tearDownClass(cls):
        cls.env['ir.config_parameter'].set_param(
            'mail_sendgrid.send_method', 'traditional')
        super(TestMailSendgrid, cls).tearDownClass()
