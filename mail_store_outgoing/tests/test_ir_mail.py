# -*- coding: utf-8 -*-
# Copyright 2018 AGENTERP GMBH
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from openerp.tests.common import TransactionCase

class TestIrMail(TransactionCase):

    def setUp(self):
        super(TestIrMail, self).setUp()

    def test_parse_list_response(self):
        imap_mailbox = '(\\HasNoChildren \\UnMarked) "." "INBOX.Deleted Messages"'
        flags, delimiter, mailbox_name = \
                self.env['ir.mail_server'].parse_list_response(imap_mailbox)
        self.assertEqual(flags, '\\HasNoChildren \\UnMarked')
        self.assertEqual(delimiter, '.')
        self.assertEqual(mailbox_name, 'INBOX.Deleted Messages')
