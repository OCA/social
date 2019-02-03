# -*- coding: utf-8 -*-
# Copyright 2019 Therp BV <https://therp.nl>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).
from mock import patch
from openerp.tests.common import TransactionCase


class TestMailQueueSendLimit(TransactionCase):
    def test_mail_queue_send_limit(self):
        limit = int(self.env.ref('mail_queue_send_limit.param_limit').value)
        for i in range(limit + 1):
            self.env['mail.mail'].create({
                'type': 'email',
                'state': 'outgoing',
            })
        with patch.object(
            self.env.registry.models['mail.mail'].__class__, 'send'
        ) as send:
            self.env['mail.mail'].process_email_queue()
            send.assert_called_once()
            self.assertEqual(
                len(send.call_args[0][2]), limit,
            )
