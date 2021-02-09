# -*- coding: utf-8 -*-
# Copyright 2018 Lorenzo Battistini - Agile Business Group
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

import odoo.tests.common as common
from odoo.modules.module import get_module_resource


class TestMailNotification(common.TransactionCase):
    def setUp(self):
        super(TestMailNotification, self).setUp()
        self.fetchmail_model = self.env['fetchmail.server']
        self.partner_model = self.env['res.partner']
        self.thread_model = self.env['mail.thread']

    def test_notify_bounce_partners(self):
        admin_id = self.partner_model.search(
            [('name', '=', 'Administrator')])[0].id
        server = self.fetchmail_model.create({
            'name': 'disabled',
            'server': 'disabled',
            'user': 'disabled',
            'password': 'disabled',
            'bounce_notify_partner_ids': [(6, 0, [admin_id])]
        })

        path = get_module_resource(
            'mail_notify_bounce',
            'tests', 'data', 'bounce_message'
        )
        with open(path) as bounce_message:
            self.thread_model.with_context(
                fetchmail_server_id=server.id
            ).message_process(
                model='res.partner', message=bounce_message.read())
        sent_mail = self.env['mail.mail'].search(
            [], order="create_date desc")[0]
        self.assertEqual(sent_mail.recipient_ids.name, 'Administrator')
        self.assertEqual(
            sent_mail.subject, 'Delivery Status Notification (Failure)')

        path = get_module_resource(
            'mail_notify_bounce',
            'tests', 'data', 'bounce_message_2'
        )
        with open(path) as bounce_message:
            self.thread_model.with_context(
                fetchmail_server_id=server.id
            ).message_process(
                model='res.partner', message=bounce_message.read())
        sent_mail = self.env['mail.mail'].search(
            [], order="create_date desc")[0]
        self.assertEqual(sent_mail.recipient_ids.name, 'Administrator')
        self.assertEqual(
            sent_mail.subject, 'Delivery Status Notification (Failure)')
