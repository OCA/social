from odoo.tests.common import TransactionCase
from odoo import exceptions, tools
from mock import patch
import base64


class TestMailDropTarget(TransactionCase):
    def setUp(self):
        super().setUp()
        self.partner = self.env['res.partner'].create({
            'name': 'TEST PARTNER'
        })
        self.partner.message_subscribe(partner_ids=self.partner.ids)

    def test_eml(self):
        message = tools.file_open(
            'sample.eml',
            subdir="addons/mail_drop_target/tests"
        ).read()
        comments = len(self.partner.message_ids)
        self.partner.message_process(
            self.partner._name, message, thread_id=self.partner.id)
        self.partner.refresh()
        self.assertEqual(comments+1, len(self.partner.message_ids))
        with self.assertRaises(exceptions.Warning):
            self.partner.message_drop(
                self.partner._name, message, thread_id=self.partner.id)

    def test_msg(self):
        message = base64.b64encode(tools.file_open(
            'sample.msg',
            mode='rb',
            subdir="addons/mail_drop_target/tests"
        ).read())
        comments = len(self.partner.message_ids)
        self.partner.message_process_msg(
            self.partner._name, message, thread_id=self.partner.id)
        self.partner.refresh()
        self.assertEqual(comments+1, len(self.partner.message_ids))
        msg = self.partner.message_ids.filtered(
            lambda m: m.subject == 'Test')
        self.assertIsNotNone(msg.needaction_partner_ids)
        with self.assertRaises(exceptions.Warning):
            self.partner.message_process_msg(
                self.partner._name, message, thread_id=self.partner.id)

    def test_no_msgextract(self):
        with self.assertRaises(exceptions.UserError), patch(
            'odoo.addons.mail_drop_target.models.mail_thread.Message',
            new=False,
        ):
            self.test_msg()

    def test_msg_no_notification(self):
        message = base64.b64encode(tools.file_open(
            'sample.msg',
            mode='rb',
            subdir="addons/mail_drop_target/tests"
        ).read())
        settings = self.env['res.config.settings'].create({})
        settings.disable_notify_mail_drop_target = True
        settings.execute()
        comments = len(self.partner.message_ids)
        self.partner.message_process_msg(
            self.partner._name, message, thread_id=self.partner.id)
        self.partner.refresh()
        self.assertEqual(comments+1, len(self.partner.message_ids))
        msg = self.partner.message_ids.filtered(
            lambda m: m.subject == 'Test')
        self.assertEqual(len(msg.needaction_partner_ids), 0)
        with self.assertRaises(exceptions.Warning):
            self.partner.message_process_msg(
                self.partner._name, message, thread_id=self.partner.id)
