# -*- coding: utf-8 -*-
# © 2015 Therp BV <http://therp.nl>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
from openerp import SUPERUSER_ID, api, models
from openerp.addons.mail.mail_thread import mail_thread


class MailThread(models.Model):
    _inherit = 'mail.thread'

    @api.multi
    def _get_subscription_data(self, name, args, user_pid=None):
        result = super(MailThread, self)._get_subscription_data(
            name, args, user_pid=user_pid)
        subtypes = self.env['mail.message.subtype'].search([
            ('hidden', '=', False),
            '|',
            ('res_model', '=', self._name),
            ('res_model', '=', False),
        ])
        for follower in self.env['mail.followers'].search([
            ('res_model', '=', self._name),
            ('res_id', 'in', result.keys()),
            ('partner_id', '=', user_pid or self.env.user.partner_id.id),
        ]):
            # values are ordered dicts, so we get the correct matches
            for subtype, data in zip(
                    subtypes,
                    result[follower.res_id]['message_subtype_data'].values()):
                data['force_mail'] = 'default'
                if subtype in follower.force_mail_subtype_ids:
                    data['force_mail'] = 'force_yes'
                elif subtype in follower.force_nomail_subtype_ids:
                    data['force_mail'] = 'force_no'
                data['force_own'] =\
                    subtype in follower.force_own_subtype_ids
        return result

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
            return map(lambda x: int(x[0]),
                       filter(lambda x: x[1][key] == value,
                              data.iteritems()))

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

    def _register_hook(self, cr):
        model_ids = self.pool['ir.model'].search(cr, SUPERUSER_ID, [])
        rebuilt = []
        for model in self.pool['ir.model'].browse(cr, SUPERUSER_ID, model_ids):
            if model.model not in self.pool:
                continue
            model_object = self.pool[model.model]
            if not isinstance(model_object, mail_thread):
                continue
            if isinstance(model_object, MailThread):
                continue
            bases = list(model_object.__class__.__bases__)
            if MailThread not in bases:
                bases.insert(1, MailThread)
            class_dict = dict(model_object.__dict__)
            class_dict['_inherit'] = model_object._name
            new_model_class = type(model_object._name, tuple(bases),
                                   class_dict)
            new_model = new_model_class._build_model(self.pool, cr)
            self.pool.models[model.model] = new_model
            new_model._prepare_setup(cr, SUPERUSER_ID)
            new_model._setup_base(cr, SUPERUSER_ID, False)
            new_model._setup_fields(cr, SUPERUSER_ID)
            rebuilt.append(new_model)
        for model in rebuilt:
            model._setup_complete(cr, SUPERUSER_ID)
        return super(MailThread, self)._register_hook(cr)
