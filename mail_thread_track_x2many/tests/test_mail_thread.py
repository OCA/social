# -*- coding: utf-8 -*-
# Copyright 2018 Therp BV <https://therp.nl>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).
from mock import patch
from openerp.tests.common import SingleTransactionCase

FIELD_DESCRIPTION = {
    'test_field_ids': {
        'type': 'one2many',
        'relation': 'mail.thread',
        'string': 'test',
    },
    'test_field2_ids': {
        'type': 'many2many',
        'relation': 'mail.thread',
        'string': 'test2',
    },
}


class TestMailThread(SingleTransactionCase):

    post_install = True
    at_install = False

    @patch(
        'openerp.addons.mail.mail_thread.mail_thread._get_tracked_fields',
        new=lambda *args, **kwargs: FIELD_DESCRIPTION
    )
    @patch(
        'openerp.addons.mail.mail_thread.mail_thread.fields_get',
        new=lambda *args, **kwargs: FIELD_DESCRIPTION,
    )
    def test_write(self, mock_obj=None):
        mail_thread_model = self.env['mail.thread']
        mail_message_model = self.env['mail.message']
        mail_thread = mail_thread_model.create({})
        mail_thread.write({  # non-existant fields, that's ok.
            'test_field_ids': [(6, 0, [10])],
            'test_field2_ids': [(6, 0, [10])]})
        mail_message = mail_message_model.search(
            [],
            order='id DESC',
            limit=1,
        )
        self.assertEquals(
            mail_message.body,
            '<ul><li>test<ul></ul></li><li>test2<ul></ul></li></ul>'
        )

        mail_thread.write({
            'test_field_ids': [(
                0,
                0,
                {'test_field_ids': {'field1': 'value1'}},
                )],
        })
        mail_message = mail_message_model.search(
            [],
            order='id DESC',
            limit=1,
        )
        self.assertEquals(
            mail_message.body,
            "<ul><li>test<ul><li>Added: test \u2192 {'field1': 'value1'}</li>"
            "</ul></li></ul>".decode('unicode-escape'),
        )

        mail_thread.write({
            'test_field_ids': [
                (1, 0, {'test_field_ids': {'field1': 'value2'}})],
        })
        mail_message = mail_message_model.search(
            [],
            order='id DESC',
            limit=1,
        )
        self.assertEquals(
            mail_message.body,
            "<ul><li>test<ul><li>Changed : test \u2192 {'field1': 'value2'}"
            "</li></ul></li></ul>".decode('unicode-escape'),
        )
