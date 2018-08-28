# -*- coding: utf-8 -*-
# Copyright 2017 LasLabs Inc.
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html).

from odoo.tests.common import TransactionCase


class TestMailMessage(TransactionCase):

    def setUp(self):
        super(TestMailMessage, self).setUp()
        partner = self.env.user.partner_id
        partner.message_post('Test Message')
        self.message = partner.message_ids[-1]

    def test_message_reply(self):
        self.assertEqual(len(self.message.message_ids), 1)
        self.message.message_post('Test Reply')
        self.assertEqual(len(self.message.message_ids), 2)
