# -*- coding: utf-8 -*-
# © 2015 Therp BV <http://therp.nl>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
from openerp import api, models


class MailNotification(models.Model):
    _inherit = 'mail.notification'

    @api.multi
    def get_partners_to_email(self, message):
        partner_ids = super(MailNotification, self)\
            .get_partners_to_email(message)
        for this in self:
            follower = self.env['mail.followers'].search([
                ('res_model', '=', message.model),
                ('res_id', '=', message.res_id),
                ('partner_id', '=', this.partner_id.id),
                '|', '|',
                ('force_nomail_subtype_ids', '=', message.subtype_id.id),
                ('force_mail_subtype_ids', '=', message.subtype_id.id),
                ('force_own_subtype_ids', '=', message.subtype_id.id),
            ])
            if not follower:
                continue
            if (message.subtype_id in follower.force_mail_subtype_ids or
                message.subtype_id in follower.force_own_subtype_ids) and\
                    this.partner_id.id not in partner_ids:
                partner_ids.append(this.partner_id.id)
            if message.subtype_id in follower.force_nomail_subtype_ids and\
                    this.partner_id.id in partner_ids:
                partner_ids.remove(this.partner_id.id)
        return partner_ids
