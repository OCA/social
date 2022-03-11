# Copyright 2017 LasLabs Inc.
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html).

import logging
import os
import threading
from email import message_from_string

from mock import MagicMock

import odoo.tools as tools
from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase

_logger = logging.getLogger(__name__)


class TestIrMailServer(TransactionCase):
    def setUp(self):
        super(TestIrMailServer, self).setUp()
        self.email_from = "derp@example.com"
        self.email_from_another = "another@example.com"
        self.Model = self.env["ir.mail_server"]
        self.parameter_model = self.env["ir.config_parameter"]
        self._delete_mail_servers()
        self.Model.create(
            {
                "name": "localhost",
                "smtp_host": "localhost",
                "smtp_from": self.email_from,
            }
        )
        message_file = os.path.join(
            os.path.dirname(os.path.realpath(__file__)), "test.msg"
        )
        with open(message_file, "r") as fh:
            self.message = message_from_string(fh.read())

    def _init_mail_server_domain_whilelist_based(self):
        self._delete_mail_servers()
        self.mail_server_domainone = self.Model.create(
            {
                "name": "sandbox domainone",
                "smtp_host": "localhost",
                "smtp_from": "notifications@domainone.com",
                "domain_whitelist": "domainone.com",
            }
        )
        self.mail_server_domaintwo = self.Model.create(
            {
                "name": "sandbox domaintwo",
                "smtp_host": "localhost",
                "smtp_from": "hola@domaintwo.com",
                "domain_whitelist": "domaintwo.com",
            }
        )
        self.mail_server_domainthree = self.Model.create(
            {
                "name": "sandbox domainthree",
                "smtp_host": "localhost",
                "smtp_from": "notifications@domainthree.com",
                "domain_whitelist": "domainthree.com,domainmulti.com",
            }
        )

    def _skip_test(self, reason):
        _logger.warn(reason)
        self.skipTest(reason)

    def _delete_mail_servers(self):
        """ Delete all available mail servers """
        all_mail_servers = self.Model.search([])
        if all_mail_servers:
            all_mail_servers.unlink()
        self.assertFalse(self.Model.search([]))

    def _send_mail(self, message=None, mail_server_id=None, smtp_server=None):
        if message is None:
            message = self.message
        connect = MagicMock()
        thread = threading.currentThread()
        thread.testing = False
        try:
            self.Model._patch_method("connect", connect)
            try:
                self.Model.send_email(message, mail_server_id, smtp_server)
            finally:
                self.Model._revert_method("connect")
        finally:
            thread.testing = True
        send_from, send_to, message_string = connect().sendmail.call_args[0]
        return message_from_string(message_string)

    def test_send_email_injects_from_no_canonical(self):
        """It should inject the FROM header correctly when no canonical name."""
        self.message.replace_header("From", "test@example.com")
        message = self._send_mail()
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
        mail_server_id = self.Model.sudo().search([], order="sequence", limit=1)[0].id
        message = self._send_mail(mail_server_id=mail_server_id)
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
        message = self._send_mail()
        self.assertEqual(message["From"], email_from)

        used_mail_server = self.Model._get_mail_sever(domain)
        used_mail_server = self.Model.browse(used_mail_server)
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
        message = self._send_mail()
        self.assertEqual(message["From"], email_from)

        used_mail_server = self.Model._get_mail_sever(domain)
        used_mail_server = self.Model.browse(used_mail_server)
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
        message = self._send_mail()
        self.assertEqual(
            message["From"], "Mitchell Admin <%s>" % expected_mail_server.smtp_from
        )

        used_mail_server = self.Model._get_mail_sever(domain)
        used_mail_server = self.Model.browse(used_mail_server)
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

        # Find config values
        config_smtp_from = tools.config.get("smtp_from")
        config_smtp_domain_whitelist = tools.config.get("smtp_domain_whitelist")
        if not config_smtp_from or not config_smtp_domain_whitelist:
            self._skip_test(
                "Cannot test transactions because there is not either smtp_from"
                " or smtp_domain_whitelist."
            )

        self.message.replace_header("From", email_from)
        message = self._send_mail()
        self.assertEqual(message["From"], "Mitchell Admin <%s>" % config_smtp_from)

        used_mail_server = self.Model._get_mail_sever("example.com")
        used_mail_server = self.Model.browse(used_mail_server)
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

        self.message.replace_header("From", email_from)
        message = self._send_mail()
        self.assertEqual(message["From"], email_from)

        used_mail_server = self.Model._get_mail_sever(domain)
        used_mail_server = self.Model.browse(used_mail_server)
        self.assertFalse(used_mail_server)

    def test_06_from_outgoing_server_no_name_from(self):
        self._init_mail_server_domain_whilelist_based()
        domain = "example.com"
        email_from = "test@%s" % domain
        expected_mail_server = self.mail_server_domainone

        self.message.replace_header("From", email_from)
        message = self._send_mail()
        self.assertEqual(message["From"], expected_mail_server.smtp_from)

        used_mail_server = self.Model._get_mail_sever(domain)
        used_mail_server = self.Model.browse(used_mail_server)
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
        message = self._send_mail()
        self.assertEqual(message["From"], email_from)

        used_mail_server = self.Model._get_mail_sever(domain)
        used_mail_server = self.Model.browse(used_mail_server)
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
        message = self._send_mail()
        self.assertEqual(message["From"], email_from)

        used_mail_server = self.Model._get_mail_sever(domain)
        used_mail_server = self.Model.browse(used_mail_server)
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
