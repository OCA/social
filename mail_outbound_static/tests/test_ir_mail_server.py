# Copyright 2017 LasLabs Inc.
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html).

import logging
import os
from email import message_from_string

import odoo.tools as tools
from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase

from odoo.addons.base.tests.common import MockSmtplibCase

_logger = logging.getLogger(__name__)


class TestIrMailServer(TransactionCase, MockSmtplibCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.email_from = "derp@example.com"
        cls.email_from_another = "another@example.com"
        cls.IrMailServer = cls.env["ir.mail_server"]
        cls.parameter_model = cls.env["ir.config_parameter"]
        cls._delete_mail_servers()
        cls.IrMailServer.create(
            {
                "name": "localhost",
                "smtp_host": "localhost",
                "smtp_from": cls.email_from,
            }
        )
        message_file = os.path.join(
            os.path.dirname(os.path.realpath(__file__)), "test.msg"
        )
        with open(message_file, "r") as fh:
            cls.message = message_from_string(fh.read())

    @classmethod
    def _delete_mail_servers(cls):
        """Delete all available mail servers"""
        all_mail_servers = cls.IrMailServer.search([])
        if all_mail_servers:
            all_mail_servers.unlink()

    def _init_mail_server_domain_whilelist_based(self):
        self._delete_mail_servers()
        self.assertFalse(self.IrMailServer.search([]))
        self.mail_server_domainone = self.IrMailServer.create(
            {
                "name": "sandbox domainone",
                "smtp_host": "localhost",
                "smtp_from": "notifications@domainone.com",
                "domain_whitelist": "domainone.com",
            }
        )
        self.mail_server_domaintwo = self.IrMailServer.create(
            {
                "name": "sandbox domaintwo",
                "smtp_host": "localhost",
                "smtp_from": "hola@domaintwo.com",
                "domain_whitelist": "domaintwo.com",
            }
        )
        self.mail_server_domainthree = self.IrMailServer.create(
            {
                "name": "sandbox domainthree",
                "smtp_host": "localhost",
                "smtp_from": "notifications@domainthree.com",
                "domain_whitelist": "domainthree.com,domainmulti.com",
            }
        )

    def _skip_test(self, reason):
        _logger.warning(reason)
        self.skipTest(reason)

    def _send_mail(
        self,
        message,
        mail_server_id=None,
        smtp_server=None,
        smtp_port=None,
        smtp_user=None,
        smtp_password=None,
        smtp_encryption=None,
        smtp_ssl_certificate=None,
        smtp_ssl_private_key=None,
        smtp_debug=False,
        smtp_session=None,
    ):
        smtp = smtp_session
        if not smtp:
            smtp = self.IrMailServer.connect(
                smtp_server,
                smtp_port,
                smtp_user,
                smtp_password,
                smtp_encryption,
                smtp_from=message["From"],
                ssl_certificate=smtp_ssl_certificate,
                ssl_private_key=smtp_ssl_private_key,
                smtp_debug=smtp_debug,
                mail_server_id=mail_server_id,
            )

        send_from, send_to, message_string = self.IrMailServer._prepare_email_message(
            message, smtp
        )
        self.IrMailServer.send_email(message)
        return message_string

    def test_send_email_injects_from_no_canonical(self):
        """It should inject the FROM header correctly when no canonical name."""
        self.message.replace_header("From", "test@example.com")
        # A mail server is configured for the email
        with self.mock_smtplib_connection():
            message = self._send_mail(self.message)
        self.assertEqual(message["From"], self.email_from)

    def test_send_email_injects_from_with_canonical(self):
        """It should inject the FROM header correctly with a canonical name.

        Note that there is an extra `<` in the canonical name to test for
        proper handling in the split.
        """
        user = "Test < User"
        self.message.replace_header("From", "%s <test@example.com>" % user)
        bounce_parameter = self.parameter_model.search(
            [("key", "=", "mail.bounce.alias")]
        )
        if bounce_parameter:
            # Remove mail.bounce.alias to test Return-Path
            bounce_parameter.unlink()
        # Also check passing mail_server_id
        mail_server_id = (
            self.IrMailServer.sudo().search([], order="sequence", limit=1)[0].id
        )
        # A mail server is configured for the email
        with self.mock_smtplib_connection():
            message = self._send_mail(self.message, mail_server_id=mail_server_id)
        self.assertEqual(message["From"], '"{}" <{}>'.format(user, self.email_from))
        self.assertEqual(
            message["Return-Path"], '"{}" <{}>'.format(user, self.email_from)
        )

    def test_01_from_outgoing_server_domainone(self):
        self._init_mail_server_domain_whilelist_based()
        domain = "domainone.com"
        email_from = "Mitchell Admin <admin@%s>" % domain
        expected_mail_server = self.mail_server_domainone

        self.message.replace_header("From", email_from)
        # A mail server is configured for the email
        with self.mock_smtplib_connection():
            message = self._send_mail(self.message)
        self.assertEqual(message["From"], email_from)

        used_mail_server = self.IrMailServer._get_mail_sever(domain)
        used_mail_server = self.IrMailServer.browse(used_mail_server)
        self.assertEqual(
            used_mail_server,
            expected_mail_server,
            "It using %s but we expect to use %s"
            % (used_mail_server.name, expected_mail_server.name),
        )

    def test_02_from_outgoing_server_domaintwo(self):
        self._init_mail_server_domain_whilelist_based()
        domain = "domaintwo.com"
        email_from = "Mitchell Admin <admin@%s>" % domain
        expected_mail_server = self.mail_server_domaintwo

        self.message.replace_header("From", email_from)
        # A mail server is configured for the email
        with self.mock_smtplib_connection():
            message = self._send_mail(self.message)
        self.assertEqual(message["From"], email_from)

        used_mail_server = self.IrMailServer._get_mail_sever(domain)
        used_mail_server = self.IrMailServer.browse(used_mail_server)
        self.assertEqual(
            used_mail_server,
            expected_mail_server,
            "It using %s but we expect to use %s"
            % (used_mail_server.name, expected_mail_server.name),
        )

    def test_03_from_outgoing_server_another(self):
        self._init_mail_server_domain_whilelist_based()
        domain = "example.com"
        email_from = "Mitchell Admin <admin@%s>" % domain
        expected_mail_server = self.mail_server_domainone

        self.message.replace_header("From", email_from)
        # A mail server is configured for the email
        with self.mock_smtplib_connection():
            message = self._send_mail(self.message)
        self.assertEqual(
            message["From"], "Mitchell Admin <%s>" % expected_mail_server.smtp_from
        )

        used_mail_server = self.IrMailServer._get_mail_sever(domain)
        used_mail_server = self.IrMailServer.browse(used_mail_server)
        self.assertEqual(
            used_mail_server,
            expected_mail_server,
            "It using %s but we expect to use %s"
            % (used_mail_server.name, expected_mail_server.name),
        )

    def test_04_from_outgoing_server_none_use_config(self):
        self._init_mail_server_domain_whilelist_based()
        domain = "example.com"
        email_from = "Mitchell Admin <admin@%s>" % domain

        self._delete_mail_servers()
        self.assertFalse(self.IrMailServer.search([]))
        # Find config values
        config_smtp_from = tools.config.get("smtp_from")
        config_smtp_domain_whitelist = tools.config.get("smtp_domain_whitelist")
        if not config_smtp_from or not config_smtp_domain_whitelist:
            self._skip_test(
                "Cannot test transactions because there is not either smtp_from"
                " or smtp_domain_whitelist."
            )

        self.message.replace_header("From", email_from)
        # A mail server is configured for the email
        with self.mock_smtplib_connection():
            message = self._send_mail(self.message)
        self.assertEqual(message["From"], "Mitchell Admin <%s>" % config_smtp_from)

        used_mail_server = self.IrMailServer._get_mail_sever("example.com")
        used_mail_server = self.IrMailServer.browse(used_mail_server)
        self.assertFalse(
            used_mail_server, "using this mail server %s" % (used_mail_server.name)
        )

    def test_05_from_outgoing_server_none_same_domain(self):
        self._init_mail_server_domain_whilelist_based()

        # Find config values
        config_smtp_from = tools.config.get("smtp_from")
        config_smtp_domain_whitelist = domain = tools.config.get(
            "smtp_domain_whitelist"
        )
        if not config_smtp_from or not config_smtp_domain_whitelist:
            self._skip_test(
                "Cannot test transactions because there is not either smtp_from"
                " or smtp_domain_whitelist."
            )

        email_from = "Mitchell Admin <admin@%s>" % domain

        self._delete_mail_servers()
        self.assertFalse(self.IrMailServer.search([]))
        self.message.replace_header("From", email_from)
        # A mail server is configured for the email
        with self.mock_smtplib_connection():
            message = self._send_mail(self.message)
        self.assertEqual(message["From"], email_from)

        used_mail_server = self.IrMailServer._get_mail_sever(domain)
        used_mail_server = self.IrMailServer.browse(used_mail_server)
        self.assertFalse(used_mail_server)

    def test_06_from_outgoing_server_no_name_from(self):
        self._init_mail_server_domain_whilelist_based()
        domain = "example.com"
        email_from = "test@%s" % domain
        expected_mail_server = self.mail_server_domainone

        self.message.replace_header("From", email_from)
        # A mail server is configured for the email
        with self.mock_smtplib_connection():
            message = self._send_mail(self.message)
        self.assertEqual(message["From"], expected_mail_server.smtp_from)

        used_mail_server = self.IrMailServer._get_mail_sever(domain)
        used_mail_server = self.IrMailServer.browse(used_mail_server)
        self.assertEqual(
            used_mail_server,
            expected_mail_server,
            "It using %s but we expect to use %s"
            % (used_mail_server.name, expected_mail_server.name),
        )

    def test_07_from_outgoing_server_multidomain_1(self):
        self._init_mail_server_domain_whilelist_based()
        domain = "domainthree.com"
        email_from = "Mitchell Admin <admin@%s>" % domain
        expected_mail_server = self.mail_server_domainthree

        self.message.replace_header("From", email_from)
        # A mail server is configured for the email
        with self.mock_smtplib_connection():
            message = self._send_mail(self.message)
        self.assertEqual(message["From"], email_from)

        used_mail_server = self.IrMailServer._get_mail_sever(domain)
        used_mail_server = self.IrMailServer.browse(used_mail_server)
        self.assertEqual(
            used_mail_server,
            expected_mail_server,
            "It using %s but we expect to use %s"
            % (used_mail_server.name, expected_mail_server.name),
        )

    def test_08_from_outgoing_server_multidomain_3(self):
        self._init_mail_server_domain_whilelist_based()
        domain = "domainmulti.com"
        email_from = "test@%s" % domain
        expected_mail_server = self.mail_server_domainthree

        self.message.replace_header("From", email_from)
        # A mail server is configured for the email
        with self.mock_smtplib_connection():
            message = self._send_mail(self.message)
        self.assertEqual(message["From"], email_from)

        used_mail_server = self.IrMailServer._get_mail_sever(domain)
        used_mail_server = self.IrMailServer.browse(used_mail_server)
        self.assertEqual(
            used_mail_server,
            expected_mail_server,
            "It using %s but we expect to use %s"
            % (used_mail_server.name, expected_mail_server.name),
        )

    def test_09_not_valid_domain_whitelist(self):
        self._init_mail_server_domain_whilelist_based()
        mail_server = self.mail_server_domainone
        mail_server.domain_whitelist = "example.com"
        error_msg = (
            "%s is not a valid domain. Please define a list of valid"
            " domains separated by comma"
        )

        with self.assertRaisesRegex(ValidationError, error_msg % "asdasd"):
            mail_server.domain_whitelist = "asdasd"

        with self.assertRaisesRegex(ValidationError, error_msg % "asdasd"):
            mail_server.domain_whitelist = "example.com, asdasd"

        with self.assertRaisesRegex(ValidationError, error_msg % "invalid"):
            mail_server.domain_whitelist = "example.com; invalid"

        with self.assertRaisesRegex(ValidationError, error_msg % ";"):
            mail_server.domain_whitelist = ";"

        with self.assertRaisesRegex(ValidationError, error_msg % "."):
            mail_server.domain_whitelist = "hola.com,."

    def test_10_not_valid_smtp_from(self):
        self._init_mail_server_domain_whilelist_based()
        mail_server = self.mail_server_domainone
        error_msg = "Not a valid Email From"

        with self.assertRaisesRegex(ValidationError, error_msg):
            mail_server.smtp_from = "asdasd"

        with self.assertRaisesRegex(ValidationError, error_msg):
            mail_server.smtp_from = "example.com"

        with self.assertRaisesRegex(ValidationError, error_msg):
            mail_server.smtp_from = "."

        mail_server.smtp_from = "notifications@test.com"
