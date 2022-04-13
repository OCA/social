# Copyright 2022 ForgeFlow S.L.
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html).

import os
import threading
from email import message_from_string

from mock import MagicMock

from odoo import _
from odoo.tests.common import TransactionCase


class TestIrMailServer(TransactionCase):
    def setUp(self):
        super(TestIrMailServer, self).setUp()
        self.smtp_server_model = self.env["ir.mail_server"]
        self.parameter_model = self.env["ir.config_parameter"]
        self.default_template = self.env.ref("mail.message_notification_email")
        self.paynow_template = self.env.ref("mail.mail_notification_paynow")
        self.server_1 = self.smtp_server_model.create(
            {
                "name": "localhost",
                "smtp_host": "localhost",
                "smtp_user": "user1@somemail.com",
            }
        )
        self.server_2 = self.smtp_server_model.create(
            {
                "name": "localhost",
                "smtp_host": "localhost",
                "smtp_user": "user2@somemail.com",
            }
        )
        self.user1 = self.env["res.users"].create(
            {
                "login": "user1@somemail.com",
                "email": "user1@somemail.com",
                "partner_id": self.env["res.partner"].create({"name": "User 1"}).id,
                "groups_id": [
                    (
                        6,
                        0,
                        [
                            self.env.ref("base.group_user").id,
                            self.env.ref("base.group_partner_manager").id,
                        ],
                    )
                ],
            }
        )
        self.user2 = self.env["res.users"].create(
            {
                "login": "user2@somemail.com",
                "email": "user2@somemail.com",
                "partner_id": self.env["res.partner"].create({"name": "User 2"}).id,
                "groups_id": [
                    (
                        6,
                        0,
                        [
                            self.env.ref("base.group_user").id,
                            self.env.ref("base.group_partner_manager").id,
                        ],
                    )
                ],
            }
        )
        self.user3 = self.env["res.users"].create(
            {
                "login": "user3@somemail.com",
                "email": "user3@somemail.com",
                "partner_id": self.env["res.partner"].create({"name": "User 3"}).id,
                "groups_id": [
                    (
                        6,
                        0,
                        [
                            self.env.ref("base.group_user").id,
                            self.env.ref("base.group_partner_manager").id,
                        ],
                    )
                ],
            }
        )
        self.partner = self.env.ref("base.res_partner_1")

        message_file = os.path.join(
            os.path.dirname(os.path.realpath(__file__)), "test.msg"
        )
        with open(message_file, "r") as fh:
            self.message = message_from_string(fh.read())

    def _send_mail(self, message=None, mail_server_id=None, smtp_server=None):
        if message is None:
            message = self.message
        connect = MagicMock()
        thread = threading.currentThread()
        thread.testing = False
        try:
            self.smtp_server_model._patch_method("connect", connect)
            try:
                self.smtp_server_model.send_email(message, mail_server_id, smtp_server)
            finally:
                self.smtp_server_model._revert_method("connect")
        finally:
            thread.testing = True
        call_args = connect.call_args
        return call_args

    def test_send_email_change_smtp_server(self):
        """It should inject the FROM header correctly when no canonical name."""
        self.message.replace_header("From", self.user1.login)
        call_args = self._send_mail()
        mail_server_id = call_args.kwargs.get("mail_server_id")
        self.assertEqual(mail_server_id, self.server_1.id)

        self.message.replace_header("From", self.user2.login)
        call_args = self._send_mail()
        mail_server_id = call_args.kwargs.get("mail_server_id")
        self.assertEqual(mail_server_id, self.server_2.id)

        self.message.replace_header("From", self.user3.login)
        call_args = self._send_mail()
        mail_server_id = call_args.kwargs.get("mail_server_id", False)
        # With this module, you always get mail server on call, only test when is not installed
        if not self.env["ir.module.module"].search(
            [("name", "=", "mail_outbound_static"), ("state", "=", "installed")]
        ):
            self.assertEqual(mail_server_id, None)

    def test_message_thread_send(self):
        mail_message_1 = self.partner.with_user(self.user1).message_post(
            body=_("Test"), subtype_xmlid="mail.mt_comment"
        )
        self.assertEqual(mail_message_1.mail_server_id.id, self.server_1.id)
        mail_message_2 = self.partner.with_user(self.user2).message_post(
            body=_("Test"), subtype_xmlid="mail.mt_comment"
        )
        self.assertEqual(mail_message_2.mail_server_id.id, self.server_2.id)
        mail_message_3 = self.partner.with_user(self.user3).message_post(
            body=_("Test"), subtype_xmlid="mail.mt_comment"
        )
        self.assertFalse(mail_message_3.mail_server_id.id)

    def _create_mail(self, from_user):
        MailMessage = self.env["mail.mail"]
        email_values = {
            "email_from": from_user.email,
            "subject": "Hello",
            "email_to": "contact@example.com",
            "reply_to": "contact@example.com",
        }
        return MailMessage.create(email_values)

    def test_mail_mail_send(self):
        mail1 = self._create_mail(self.user1)
        mail2 = self._create_mail(self.user2)
        mail3 = self._create_mail(self.user3)
        (mail1 + mail2 + mail3).send()
        self.assertEqual(mail1.mail_server_id.id, self.server_1.id)
        self.assertEqual(mail2.mail_server_id.id, self.server_2.id)
        self.assertFalse(mail3.mail_server_id.id)
