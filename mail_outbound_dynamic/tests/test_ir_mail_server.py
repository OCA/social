# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html).

from odoo.tests.common import TransactionCase
import odoo.tools as tools
from email import message_from_string
from mock import MagicMock
import os
import threading
import logging

_logger = logging.getLogger(__name__)


class MailOutboundDynamic(TransactionCase):

    def setUp(self):
        super().setUp()
        self.mail_server_model = self.env["ir.mail_server"]
        self._delete_mail_servers()

        self.mail_server_domainone = self.mail_server_model.create({
            "name": "sandbox domainone",
            "smtp_host": "localhost",
            "smtp_from": 'notifications@domainone.com',
            "allowed_domain": 'domainone.com',
        })
        self.mail_server_domaintwo = self.mail_server_model.create({
            "name": "sandbox domaintwo",
            "smtp_host": "localhost",
            "smtp_from": 'hola@domaintwo.com',
            "allowed_domain": 'domaintwo.com',
        })

        message_file = os.path.join(
            os.path.dirname(os.path.realpath(__file__)), "test.msg"
        )
        with open(message_file, "r") as fh:
            self.message = message_from_string(fh.read())

    def _skip_test(self, reason):
        _logger.warn(reason)
        self.skipTest(reason)

    def _delete_mail_servers(self):
        """ Delete all available mail servers """
        all_mail_servers = self.mail_server_model.search([])
        if all_mail_servers:
            all_mail_servers.unlink()
        self.assertFalse(self.mail_server_model.search([]))

    def _send_mail(self, message=None, mail_server_id=None, smtp_server=None):
        if message is None:
            message = self.message
        connect = MagicMock()
        thread = threading.currentThread()
        thread.testing = False
        try:
            self.mail_server_model._patch_method("connect", connect)
            try:
                self.mail_server_model.send_email(message, mail_server_id, smtp_server)
            finally:
                self.mail_server_model._revert_method("connect")
        finally:
            thread.testing = True
        send_from, send_to, message_string = connect().sendmail.call_args[0]
        return message_from_string(message_string)

    def test_1_from_outgoing_server_domainone(self):
        domain = 'domainone.com'
        email_from = "Mitchell Admin <admin@%s>" % domain
        expected_mail_server = self.mail_server_domainone

        self.message.replace_header("From", email_from)
        message = self._send_mail()
        self.assertEqual(message["From"], email_from)

        used_mail_server = self.mail_server_model._get_mail_sever(False, False, domain)
        self.assertEqual(used_mail_server, expected_mail_server, 'It using %s but we expect to use %s' % (
            used_mail_server.name, expected_mail_server.name))

    def test_2_from_outgoing_server_domaintwo(self):
        domain = 'domaintwo.com'
        email_from = "Mitchell Admin <admin@%s>" % domain
        expected_mail_server = self.mail_server_domaintwo

        self.message.replace_header("From", email_from)
        message = self._send_mail()
        self.assertEqual(message["From"], email_from)

        used_mail_server = self.mail_server_model._get_mail_sever(False, False, domain)
        self.assertEqual(used_mail_server, expected_mail_server, 'It using %s but we expect to use %s' % (
            used_mail_server.name, expected_mail_server.name))

    def test_3_from_outgoing_server_another(self):
        domain = 'example.com'
        email_from = "Mitchell Admin <admin@%s>" % domain
        expected_mail_server = self.mail_server_domainone

        self.message.replace_header("From", email_from)
        message = self._send_mail()
        self.assertEqual(message["From"], "Mitchell Admin <%s>" % expected_mail_server.smtp_from)

        used_mail_server = self.mail_server_model._get_mail_sever(False, False, domain)
        self.assertEqual(used_mail_server, expected_mail_server, 'It using %s but we expect to use %s' % (
            used_mail_server.name, expected_mail_server.name))

    def test_4_from_outgoing_server_none_use_config(self):
        domain = 'example.com'
        email_from = "Mitchell Admin <admin@%s>" % domain

        self._delete_mail_servers()

        # Find config values
        config_smtp_from = tools.config.get('smtp_from')
        config_smtp_allowed_domain = tools.config.get('smtp_allowed_domain')
        if not config_smtp_from or not config_smtp_allowed_domain:
            self._skip_test('Cannot test transactions because there is not smtp_from or smtp_allowed_domain.')

        self.message.replace_header("From", email_from)
        message = self._send_mail()
        self.assertEqual(message["From"], "Mitchell Admin <%s>" % config_smtp_from)

        used_mail_server = self.mail_server_model._get_mail_sever(False, False, 'example.com')
        self.assertFalse(used_mail_server, 'using this mail server %s' % (used_mail_server.name))

    def test_5_from_outgoing_server_none_same_domain(self):
        domain = 'nubeadhoc.com.ar'
        email_from = "Mitchell Admin <admin@%s>" % domain

        self._delete_mail_servers()

        # Find config values
        config_smtp_from = tools.config.get('smtp_from')
        config_smtp_allowed_domain = tools.config.get('smtp_allowed_domain')
        if not config_smtp_from or not config_smtp_allowed_domain:
            self._skip_test('Cannot test transactions because there is not smtp_from or smtp_allowed_domain.')

        self.message.replace_header("From", email_from)
        message = self._send_mail()
        self.assertEqual(message["From"], email_from)

        used_mail_server = self.mail_server_model._get_mail_sever(False, False, domain)
        self.assertFalse(used_mail_server)

    def test_6_from_outgoing_server_no_name_from(self):
        domain = 'example.com'
        email_from = "test@%s" % domain
        expected_mail_server = self.mail_server_domainone

        self.message.replace_header("From", email_from)
        message = self._send_mail()
        self.assertEqual(message["From"], expected_mail_server.smtp_from)

        used_mail_server = self.mail_server_model._get_mail_sever(False, False, domain)
        self.assertEqual(used_mail_server, expected_mail_server, 'It using %s but we expect to use %s' % (
            used_mail_server.name, expected_mail_server.name))
