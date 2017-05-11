# -*- coding: utf-8 -*-
# © 2017 initOS GmbH <https://www.initos.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
import mock

from openerp.tests.common import TransactionCase


class TestBaseMailBcc(TransactionCase):
    def test_base_mail_bcc(self):
        ir_mail_server = self.env['ir.mail_server']
        message = ir_mail_server.build_email(
            email_from='admin@example.com',
            email_to='admin@example.com',
            email_bcc='unused@example.com',
            subject='An example E-Mail',
            body='With an example body',
        )
        with mock.patch("smtplib.SMTP"):
            ir_mail_server.send_email(message)
