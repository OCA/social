# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
from openerp.tests.common import TransactionCase


class TestMailEdit(TransactionCase):

    def setUp(self, *args, **kwargs):
        # make sale.order and res_partner allowed to edit
        super(TestMailEdit, self).setUp(*args, **kwargs)
        self.rrl_partner = self.env['res.request.link'].create({
            'name': 'A partner',
            'object': 'res.partner',
            'priority': 1,
            'mail_edit': True,
        })
        self.rrl_partner_2 = self.env['res.request.link'].create({
            'name': 'Another partner',
            'object': 'res.partner',
            'priority': 2,
            'mail_edit': True,
        })
        self.sender = self.env['res.partner'].create({
            'name': 'Test sender',
            'email': 'sender@example.com',
            'notify_email': 'always',
        })
        self.recipient = self.env['res.partner'].create({
            'name': 'Test recipient',
            'email': 'recipient@example.com',
            'notify_email': 'always',
        })
        self.message = self.env['mail.message'].create({
            'subject': 'Message test',
            'author_id': self.sender.id,
            'email_from': self.sender.email,
            'message_type': 'comment',
            'model': 'res.partner',
            'res_id': self.recipient.id,
            'partner_ids': [(4, self.recipient.id)],
            'body': '<p>This is not a test message</p>',
        })

    def test_change_destination_object(self):
        objects = self.message._get_model_selection()
        self.assertEqual(len(objects), 3)
        self.assertFalse(self.message.destination_object_id)
        self.assertTrue(
            self.message.model and
            self.message.res_id and
            self.message.record_name
        )
        # call onchange manually to nullify .model, .res_id, .record_name
        self.message.change_destination_object()
        self.assertFalse(
            self.message.model and
            self.message.res_id and
            self.message.record_name
        )
        # create an arbitrary object from base
        arbitrary_object = self.env['res.request.link'].create({
            'name': 'Colombia',
            'object': 'res.country',
            'priority': 3,
            'mail_edit': True,
        })
        # recalculate selection to include arbitrary_object
        self.message._get_model_selection()
        # Set a value to reference field
        self.message.destination_object_id = "{},{}".format(
            arbitrary_object.object, arbitrary_object.id
        )
        self.assertTrue(self.message.destination_object_id)
        # call onchange manually to get values from reference
        self.message.change_destination_object()
        self.assertTrue(
            self.message.model and
            self.message.res_id and
            self.message.record_name
        )
        self.assertEqual(self.message.model, 'res.country')
        self.assertEqual(self.message.res_id, arbitrary_object.id)

    def test_message_read_dict_postprocess(self):
        message = [self.message._message_read_dict()]
        all_messages = self.env['mail.message'].search([])
        message_tree = dict((m.id, m) for m in all_messages)
        # do stuff to the message
        self.message._message_read_dict_postprocess(message, message_tree)
        message_list = self.message.message_format()
        self.assertTrue(message_list[0].get('is_superuser', False))
