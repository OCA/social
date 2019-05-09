# Copyright 2018 AGENTERP GMBH
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo.exceptions import ValidationError
from openerp.tests import common


class TestIrMail(common.TransactionCase):

    def setUp(self):
        super(TestIrMail, self).setUp()
        self.mail_server = self.env['ir.mail_server'].create({
            'smtp_port': '25',
            'smtp_host': 'localhost',
            'smtp_encryption': 'none',
            'name': 'test',
            'has_separate_imap_server': True,
            'store_outgoing_mail': True,
        })

    def test_parse_list_response(self):
        imap_mailbox = \
            b'(\\HasNoChildren \\UnMarked) "." "INBOX.Deleted Messages"'
        flags, delimiter, mailbox_name = \
            self.env['ir.mail_server'].parse_list_response(imap_mailbox)
        self.assertEqual(flags, '\\HasNoChildren \\UnMarked')
        self.assertEqual(delimiter, '.')
        self.assertEqual(mailbox_name, 'INBOX.Deleted Messages')

    def test_imap_connection(self):
        try:
            self.mail_server.test_imap_connection()
        except ValidationError as e:
            pass

    def test_send_mail(self):
        msg = self.env['ir.mail_server'].build_email(
            email_from='test.from@example.com',
            reply_to='test.reply@example.com',
            email_to=["test.to@example.com"],
            subject="Test Subject",
            body="test Bosy",
        )
        self.env['ir.mail_server'].send_email(
            msg, mail_server_id=self.mail_server.id)

    def test_save_sent_message_to_sentbox(self):
        msg = self.env['ir.mail_server'].build_email(
            email_from='test.from@example.com',
            reply_to='test.reply@example.com',
            email_to=["test.to@example.com"],
            subject="Test Subject",
            body="test Bosy",
        )
        msg = self.env['ir.mail_server']._save_sent_message_to_sentbox(
            msg, self.mail_server.id)
