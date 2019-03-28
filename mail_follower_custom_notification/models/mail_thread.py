# -*- coding: utf-8 -*-
# Copyright 2015 Therp BV <http://therp.nl>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
from odoo import api, models


class MailThread(models.AbstractModel):
    _inherit = 'mail.thread'

    @api.multi
    def message_custom_notification_update_user(self, custom_notifications):
        """change custom_notifications from user ids to partner ids"""
        user2partner = dict(
            self.env['res.users'].browse(map(int, custom_notifications.keys()))
            .mapped(lambda user: (str(user.id), str(user.partner_id.id)))
        )
        return self.message_custom_notification_update({
            user2partner[user_id]: data
            for user_id, data in custom_notifications.iteritems()
        })

    @api.multi
    def message_custom_notification_update(self, custom_notifications):
        """custom_notifications is a dictionary with partner ids as keys
        and dictionaries mapping message subtype ids to custom notification
        values"""
        def ids_with_value(data, key, value):
            return map(
                lambda x: int(x[0]),
                filter(lambda x: x[1][key] == value, data.iteritems())
            )

        custom_notifications = {
            int(key): value
            for key, value in custom_notifications.iteritems()
            if key != 'False'
        }

        for follower in self.env['mail.followers'].search([
            ('res_model', '=', self._name),
            ('res_id', 'in', self.ids),
            ('partner_id', 'in', custom_notifications.keys()),
        ]):
            data = custom_notifications[follower.partner_id.id]
            follower.write({
                'force_mail_subtype_ids': [(6, 0, ids_with_value(
                    data, 'force_mail', 'force_yes'))],
                'force_nomail_subtype_ids': [(6, 0, ids_with_value(
                    data, 'force_mail', 'force_no'))],
                'force_own_subtype_ids': [(6, 0, ids_with_value(
                    data, 'force_own', '1'))]
            }),
