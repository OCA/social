# -*- coding: utf-8 -*-
# © 2015 Therp BV <http://therp.nl>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
from openerp.tests.common import TransactionCase


class TestMailFollowerCustomNotification(TransactionCase):
    def test_mail_follower_custom_notification(self):
        self.env['mail.thread']._register_hook()
        followed_partner = self.env['res.partner'].create({
            'name': 'I\'m followed',
        })
        demo_user = self.env.ref('base.user_demo')
        followed_partner_demo = followed_partner.sudo(demo_user.id)
        followed_partner_demo.message_subscribe_users()

        # see if default subscriptions return default custom settings
        subscription_data = followed_partner_demo._get_subscription_data(
            None, None)
        self.assertEqual(
            subscription_data[followed_partner.id]['message_subtype_data']
            ['Discussions']['force_mail'],
            'default')
        self.assertEqual(
            subscription_data[followed_partner.id]['message_subtype_data']
            ['Discussions']['force_own'],
            False)

        # set custom settings
        mt_comment = self.env.ref('mail.mt_comment')
        followed_partner_demo.message_custom_notification_update_user({
            str(demo_user.id): {
                str(mt_comment.id): {
                    'force_mail': 'force_yes',
                    'force_own': '1',
                },
            },
        })
        # see if we can read them back
        subscription_data = followed_partner_demo._get_subscription_data(
            None, None)
        self.assertEqual(
            subscription_data[followed_partner.id]['message_subtype_data']
            ['Discussions']['force_mail'],
            'force_yes')
        self.assertEqual(
            subscription_data[followed_partner.id]['message_subtype_data']
            ['Discussions']['force_own'],
            True)

        # post a message and see if we successfully forced a notification to
        # ourselves
        followed_partner_demo.message_post('hello world', subtype='mt_comment')
        self.assertEqual(
            followed_partner_demo.message_ids[:-1].notification_ids.partner_id,
            demo_user.partner_id)

        # assign default values on message subtype and apply them to all
        # followers
        mt_comment.custom_notification_model_ids = self.env['ir.model']\
            .search([('model', '=', 'res.partner')])
        wizard = self.env['mail.subtype.assign.custom.notifications']\
            .with_context(active_ids=mt_comment.ids)\
            .create({})
        wizard.button_apply()
        subscription_data = followed_partner_demo._get_subscription_data(
            None, None)
        self.assertEqual(
            subscription_data[followed_partner.id]['message_subtype_data']
            ['Discussions']['force_mail'],
            'default')
        self.assertEqual(
            subscription_data[followed_partner.id]['message_subtype_data']
            ['Discussions']['force_own'],
            False)
