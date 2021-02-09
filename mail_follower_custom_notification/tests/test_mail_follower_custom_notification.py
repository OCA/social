# -*- coding: utf-8 -*-
# Copyright 2015 Therp BV <http://therp.nl>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
from mock import Mock, patch
from openerp.tests.common import TransactionCase
from ..controllers.mail_controller import MailController


class TestMailFollowerCustomNotification(TransactionCase):
    def _call_controller(self, res_model, follower_id):
        mt_comment = self.env.ref('mail.mt_comment')
        with patch('__builtin__.super') as mock_super, patch(
                'odoo.addons.mail_follower_custom_notification.controllers.'
                'mail_controller.request'
        ) as mock_request:
            mock_super.return_value = Mock(
                read_subscription_data=lambda res_model, follower_id: [{
                    'id': mt_comment.id,
                }],
            )
            mock_request.env = self.env
            return MailController.read_subscription_data.__func__(
                None, res_model, follower_id,
            )[0]

    def test_mail_follower_custom_notification(self):
        followed_partner = self.env['res.partner'].create({
            'name': 'I\'m followed',
        })
        demo_user = self.env.ref('base.user_demo')
        mt_comment = self.env.ref('mail.mt_comment')
        followed_partner_demo = followed_partner.sudo(demo_user.id)
        followed_partner_demo.message_subscribe_users()
        follower = followed_partner_demo.message_follower_ids.filtered(
            lambda x: x.partner_id == demo_user.partner_id
        )

        # see if default subscriptions return default custom settings
        subscription_data = self._call_controller(
            follower.res_model, follower.id,
        )
        self.assertEqual(subscription_data['force_mail'], 'default')
        self.assertEqual(subscription_data['force_own'], False)

        # set custom settings
        followed_partner_demo.message_custom_notification_update_user({
            str(demo_user.id): {
                str(mt_comment.id): {
                    'force_mail': 'force_yes',
                    'force_own': '1',
                },
            },
        })
        # see if we can read them back
        subscription_data = self._call_controller(
            follower.res_model, follower.id,
        )
        self.assertEqual(subscription_data['force_mail'], 'force_yes')
        self.assertEqual(subscription_data['force_own'], True)

        # post a message and see if we successfully forced a notification to
        # ourselves
        # pylint: disable=translation-required
        followed_partner_demo.message_post('hello world', subtype='mt_comment')
        self.assertIn(
            demo_user.partner_id,
            followed_partner_demo.message_ids[:-1].notification_ids.mapped(
                'res_partner_id',
            )
        )

        # assign default values on message subtype and apply them to all
        # followers
        mt_comment.custom_notification_model_ids = self.env['ir.model'].search(
            [('model', '=', 'res.partner')]
        )
        wizard = self.env['mail.subtype.assign.custom.notifications']\
            .with_context(active_ids=mt_comment.ids)\
            .create({})
        wizard.button_apply()
        subscription_data = self._call_controller(
            follower.res_model, follower.id,
        )
        self.assertEqual(subscription_data['force_mail'], 'default')
        self.assertEqual(subscription_data['force_own'], False)
