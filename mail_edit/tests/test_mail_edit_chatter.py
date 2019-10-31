# Copyright 2019 Creu Blanca
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo.tests.common import TransactionCase


class TestMailEditChatter(TransactionCase):
    def setUp(self):
        super().setUp()
        self.partner_id = self.env['res.partner'].create({
            'name': 'Test Record'
        })

    def test_edit_message(self):
        message = self.partner_id.message_post(
            subject='Test Message',
            body='Hello',
            message_type='comment'
        )
        self.assertFalse(message.edited)

        edit_wizz = self.env['wizard.edit.message'].with_context(
            mail_message_id=message.id
        ).create({})
        edit_wizz.write({'message': 'Bye bye'})
        edit_wizz.save_message_changes()
        self.assertTrue(message.edited)
        self.assertEqual(message.edited_message_ids[0].body, '<p>Hello</p>')

        view_editions = self.env['wizard.view.previous.editions'].with_context(
            mail_message_id=message.id
        ).create({})
        self.assertTrue(view_editions.edited_message_ids)
