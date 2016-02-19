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
    @api.returns('self', lambda x: x.id)
    def create(self, values):
        this = super(MailFollowers, self).create(values)
        for subtype in this.subtype_ids:
            if not subtype.res_model and\
                    subtype.custom_notification_model_ids and\
                    this.res_model not in\
                    subtype.custom_notification_model_ids\
                        .mapped('model'):
                continue
            if subtype.custom_notification_mail == 'force_yes':
                this.force_mail_subtype_ids += subtype
            if subtype.custom_notification_mail == 'force_no':
                this.force_nomail_subtype_ids += subtype
            if subtype.custom_notification_own:
                this.force_own_subtype_ids += subtype
        return this
