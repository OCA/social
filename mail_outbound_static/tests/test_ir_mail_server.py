# Copyright 2017 LasLabs Inc.
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html).

import os
import threading

from mock import MagicMock
from email import message_from_string

from odoo.tests.common import TransactionCase


class TestIrMailServer(TransactionCase):

    def setUp(self):
        super(TestIrMailServer, self).setUp()
        self.email_from = 'derp@example.com'
        self.email_from_another = 'another@example.com'
        self.Model = self.env['ir.mail_server']
        self.parameter_model = self.env['ir.config_parameter']
        self.Model.create({
            'name': 'localhost',
            'smtp_host': 'localhost',
            'smtp_from': self.email_from,
        })
        message_file = os.path.join(
            os.path.dirname(os.path.realpath(__file__)), 'test.msg',
        )
        with open(message_file, 'r') as fh:
            self.message = message_from_string(fh.read())

    def _send_mail(self, message=None, mail_server_id=None, smtp_server=None):
        if message is None:
            message = self.message
        connect = MagicMock()
        thread = threading.currentThread()
        setattr(thread, 'testing', False)
        try:
            self.Model._patch_method('connect', connect)
            try:
                self.Model.send_email(message, mail_server_id, smtp_server)
            finally:
                self.Model._revert_method('connect')
        finally:
            setattr(thread, 'testing', True)
        send_from, send_to, message_string = connect().sendmail.call_args[0]
        return message_from_string(message_string)

    def test_send_email_injects_from_no_canonical(self):
        """It should inject the FROM header correctly when no canonical name.
        """
        self.message.replace_header('From', 'test@example.com')
        message = self._send_mail()
        self.assertEqual(message['From'], self.email_from)

    def test_send_email_injects_from_with_canonical(self):
        """It should inject the FROM header correctly with a canonical name.

        Note that there is an extra `<` in the canonical name to test for
        proper handling in the split.
        """
        user = 'Test < User'
        self.message.replace_header('From', '%s <test@example.com>' % user)
        bounce_parameter = self.parameter_model.search([
            ('key', '=', 'mail.bounce.alias')])
        if bounce_parameter:
            # Remove mail.bounce.alias to test Return-Path
            bounce_parameter.unlink()
        # Also check passing mail_server_id
        mail_server_id = self.Model.sudo().search(
            [], order='sequence', limit=1)[0].id
        message = self._send_mail(mail_server_id=mail_server_id)
        self.assertEqual(
            message['From'],
            '%s <%s>' % (user, self.email_from),
        )
        self.assertEqual(
            message['Return-Path'],
            '%s <%s>' % (user, self.email_from),
        )
