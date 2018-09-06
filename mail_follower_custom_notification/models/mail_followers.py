# -*- coding: utf-8 -*-
# © 2015 Therp BV <http://therp.nl>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
from openerp import api, fields, models


class MailFollowers(models.Model):
    _inherit = 'mail.followers'

    force_mail_subtype_ids = fields.Many2many(
        'mail.message.subtype', 'mail_followers_force_mail_rel',
        'mail_followers_id', 'mail_message_subtype_id',
        string='Force mails from subtype')

    force_nomail_subtype_ids = fields.Many2many(
        'mail.message.subtype', 'mail_followers_force_nomail_rel',
        'mail_followers_id', 'mail_message_subtype_id',
        string='Force no mails from subtype')

    force_own_subtype_ids = fields.Many2many(
        'mail.message.subtype', 'mail_followers_force_own_rel',
        'mail_followers_id', 'mail_message_subtype_id',
        string='Force own mails from subtype')

    @api.model
    def create(self, values):
        this = super(MailFollowers, self).create(values)
        this._mail_follower_custom_notification_update()
        return this

    @api.multi
    def _mail_follower_custom_notification_update(self, subtypes=None):
        self.ensure_one()
        for subtype in subtypes or self.subtype_ids:
            if not subtype.res_model and\
                    subtype.custom_notification_model_ids and\
                    self.res_model not in\
                    subtype.custom_notification_model_ids\
                        .mapped('model'):
                continue
            user = self.env['res.users'].search([
                ('partner_id', '=', self.partner_id.id),
            ], limit=1)
            is_employee = user and user.has_group('base.group_user')
            if subtype.custom_notification_mail == 'force_yes':
                self.force_mail_subtype_ids |= subtype
            if subtype.custom_notification_mail == 'force_no':
                self.force_nomail_subtype_ids |= subtype
            if is_employee:
                if subtype.custom_notification_mail_employees == 'force_yes':
                    self.force_mail_subtype_ids |= subtype
                    self.force_nomail_subtype_ids -= subtype
                if subtype.custom_notification_mail_employees == 'force_no':
                    self.force_mail_subtype_ids -= subtype
                    self.force_nomail_subtype_ids |= subtype
            if subtype.custom_notification_own:
                self.force_own_subtype_ids |= subtype

    @api.multi
    def write(self, values):
        result = super(MailFollowers, self).write(values)
        if 'subtype_ids' in values:
            for this in self:
                subtypes = self.env['mail.message.subtype'].browse(
                    filter(
                        None,
                        map(
                            lambda x: x.get('id'),
                            this.resolve_2many_commands(
                                'subtype_ids', values['subtype_ids'],
                            ),
                        )
                    )
                )
                this._mail_follower_custom_notification_update(subtypes)
        return result
