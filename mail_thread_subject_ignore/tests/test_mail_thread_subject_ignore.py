# Copyright 2023 ForgeFlow S. L.
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

import email
import os

from odoo import tools
from odoo.tests.common import TransactionCase, tagged


@tagged("mail_gateway")
class TestFetchmailIncomingLog(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super(TestFetchmailIncomingLog, cls).setUpClass()

        cls.fetchmail_server = cls.env["fetchmail.server"].create(
            {"name": "Test Fetchmail Server", "server_type": "imap"}
        )

    def test_01_ignore_email(self):
        """
        Check the automatic reply is ignored
        and the others are not
        """

        def emulate_imap_fetch(email_content):
            # Parse the email content
            msg = email.message_from_string(email_content)
            # Emulate the result and data similar to imaplib's fetch method
            result = "OK"
            msg_str = msg.as_string()
            data = msg_str  # f"1 (RFC822 {{{len(msg_str)}}})\r\n{msg_str}\r\n"
            return result, data

        mail_file = os.path.join(
            os.path.dirname(os.path.realpath(__file__)), "sample_email.eml"
        )
        with open(mail_file, "r") as f:
            email_content = f.read()

        result, data = emulate_imap_fetch(email_content)
        data = data.encode("utf-8")
        message = email.message_from_bytes(data, policy=email.policy.SMTP)
        tools.decode_message_header(message, "From")
        self.env["mail.thread"].message_parse(message, save_original=False)
        res_id = (
            self.env["mail.thread"]
            .with_context(**{"default_fetchmail_server_id": self.fetchmail_server.id})
            .message_process(
                "res.partner", data, save_original=False, strip_attachments=False
            )
        )
        self.assertEqual(res_id, None)
        mail_file = os.path.join(
            os.path.dirname(os.path.realpath(__file__)), "sample_email2.eml"
        )
        with open(mail_file, "r") as f:
            email_content = f.read()

        result, data = emulate_imap_fetch(email_content)
        data = data.encode("utf-8")
        message = email.message_from_bytes(data, policy=email.policy.SMTP)
        tools.decode_message_header(message, "From")
        self.env["mail.thread"].message_parse(message, save_original=False)
        res_id = (
            self.env["mail.thread"]
            .with_context(**{"default_fetchmail_server_id": self.fetchmail_server.id})
            .message_process(
                "res.partner", data, save_original=False, strip_attachments=False
            )
        )
        self.assertTrue(isinstance(res_id, int))
