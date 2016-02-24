# -*- coding: utf-8 -*-
# © 2015 Therp BV <http://therp.nl>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
from openerp import api, fields, models


class MailSubtypeAssignCustomNotifications(models.TransientModel):
    _name = 'mail.subtype.assign.custom.notifications'
    _description = 'Assign custom notification settings to existing followers'

    subtype_ids = fields.Many2many(
        'mail.message.subtype', 'mail_subtype_assign_custom_notifications_rel',
        string='Subtypes', required=True,
        default=lambda self: [(6, 0, self.env.context.get('active_ids', []))])

    @api.multi
    def button_apply(self):
        self.ensure_one()
        for subtype in self.subtype_ids:
            domain = [('subtype_ids', '=', subtype.id)]
            if subtype.custom_notification_model_ids:
                domain.append(
                    ('res_model', 'in',
                     subtype.custom_notification_model_ids.mapped('model')))
            self.env['mail.followers'].with_context(active_test=False)\
                .search(domain)\
                .write({
                    'force_mail_subtype_ids': [
                        (4, subtype.id)
                        if subtype.custom_notification_mail == 'force_yes'
                        else
                        (3, subtype.id)
                    ],
                    'force_nomail_subtype_ids': [
                        (4, subtype.id)
                        if subtype.custom_notification_mail == 'force_no'
                        else
                        (3, subtype.id)
                    ],
                    'force_own_subtype_ids': [
                        (4, subtype.id)
                        if subtype.custom_notification_own
                        else
                        (3, subtype.id)
                    ],
                })
