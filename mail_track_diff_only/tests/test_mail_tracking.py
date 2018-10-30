# coding: utf-8
from odoo import api
from odoo.tests import common


class TestTracking(common.TransactionCase):

    def test_message_track(self):
        self.user_group_employee = self.env.ref('base.group_user')
        users = self.env['res.users'].with_context({
            'no_reset_password': True, 'mail_create_nosubscribe': True})
        self.user_employee = users.create({
            'name': 'Ernest Employee',
            'login': 'ernest',
            'email': 'e.e@example.com',
            'signature': '--\nErnest',
            'notification_type': 'email',
            'groups_id': [(6, 0, [self.user_group_employee.id])]
        })
        test_channel = self.env['mail.channel'].create({
            'name': 'Test',
            'channel_partner_ids': [(4, self.user_employee.partner_id.id)]
        })

        subtype = self.env['mail.message.subtype']
        data = self.env['ir.model.data']
        note_subtype = self.env.ref('mail.mt_note')

        # mt_private: public field (tracked as onchange) set to 'private'
        # (selection)
        mt_private = subtype.create({
            'name': 'private',
            'description': 'Public field set to private'
        })
        data.create({
            'name': 'mt_private',
            'model': 'mail.message.subtype',
            'module': 'mail',
            'res_id': mt_private.id
        })

        # mt_name_supername: name field (tracked as always) set to 'supername'
        # (char)
        mt_name_supername = subtype.create({
            'name': 'name_supername',
            'description': 'Name field set to supername'
        })
        data.create({
            'name': 'mt_name_supername',
            'model': 'mail.message.subtype',
            'module': 'mail',
            'res_id': mt_name_supername.id
        })

        # mt_group_public_set: group_public field (tracked as onchange) set to
        # something (m2o)
        mt_group_public_set = subtype.create({
            'name': 'group_public_set',
            'description': 'Group_public field set'
        })
        data.create({
            'name': 'mt_group_public_set',
            'model': 'mail.message.subtype',
            'module': 'mail',
            'res_id': mt_group_public_set.id
        })

        # mt_group_public_set: group_public field (tracked as onchange) set to
        # nothing (m2o)
        mt_group_public_unset = subtype.create({
            'name': 'group_public_unset',
            'description': 'Group_public field unset'
        })
        data.create({
            'name': 'mt_group_public_unset',
            'model': 'mail.message.subtype',
            'module': 'mail',
            'res_id': mt_group_public_unset.id
        })

        @api.multi
        def _track_subtype(self, init_values):
            if 'public' in init_values and self.public == 'private':
                return 'mail.mt_private'
            elif 'name' in init_values and self.name == 'supername':
                return 'mail.mt_name_supername'
            elif 'group_public_id' in init_values and self.group_public_id:
                return 'mail.mt_group_public_set'
            elif 'group_public_id' in init_values and not self.group_public_id:
                return 'mail.mt_group_public_unset'
            return False
        self.registry('mail.channel')._patch_method(
            '_track_subtype', _track_subtype)

        visibility = {
            'public': 'onchange',
            'name': 'always',
            'group_public_id': 'onchange'
        }
        channel = type(self.env['mail.channel'])
        for key in visibility:
            self.assertFalse(
                hasattr(getattr(channel, key), 'track_visibility'))
            getattr(channel, key).track_visibility = visibility[key]

        # Test: change name -> always tracked, not related to a subtype
        test_channel.sudo(self.user_employee).write({'name': 'my_name'})
        self.assertEqual(len(test_channel.message_ids), 1)
        last_msg = test_channel.message_ids[-1]
        self.assertEqual(last_msg.subtype_id, note_subtype)
        self.assertEqual(len(last_msg.tracking_value_ids), 1)
        self.assertEqual(last_msg.tracking_value_ids.field, 'name')
        self.assertEqual(last_msg.tracking_value_ids.field_desc, 'Name')
        self.assertEqual(last_msg.tracking_value_ids.old_value_char, 'Test')
        self.assertEqual(last_msg.tracking_value_ids.new_value_char, 'my_name')
