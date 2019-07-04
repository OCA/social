# Copyright 2019 Eficent Business and IT Consulting Services, S.L.
# Copyright 2019 Aleph Objects, Inc.
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from odoo.tests.common import TransactionCase


class TestMessageAutoSubscribeNotifyOwn(TransactionCase):

    def setUp(self):
        super(TestMessageAutoSubscribeNotifyOwn, self).setUp()

        self.user_root = self.env.ref('base.user_root')
        self.user_root.notification_type = 'email'

        self.fake_model_id = self.env['ir.model'].search(
            [('model', '=', 'message_auto_subscribe_notify_own.test')])

        self.env['auto.subscribe.notify.own.model'].create(dict(
            model_id=self.fake_model_id.id
        ))
        self.fake_test = self.env[
            'message_auto_subscribe_notify_own.test'].create(
            dict(name='Test Fake Model',
                 user_id=self.env.ref('base.user_demo').id))

    def tearDown(self):
        super(TestMessageAutoSubscribeNotifyOwn, self).tearDown()

    def test_message_auto_subscribe_notify_own(self):
        prev_mail_messages = self.env['mail.message'].search([
            ('model', '=', 'message_auto_subscribe_notify_own.test'),
            ('res_id', '=', self.fake_test.id),
        ])
        self.fake_test.update(dict(
            user_id=self.user_root.id
        ))
        mail_messages = self.env['mail.message'].search([
            ('model', '=', 'message_auto_subscribe_notify_own.test'),
            ('res_id', '=', self.fake_test.id),
        ])
        self.assertEqual(len(mail_messages-prev_mail_messages), 1)

    def test_compute_name(self):
        notified_model = self.env['auto.subscribe.notify.own.model'].search(
            [('model_id', '=', self.fake_model_id.id)])
        notified_model._compute_name()
        self.assertTrue(notified_model.name,
                        'message_auto_subscribe_notify_own.test')
