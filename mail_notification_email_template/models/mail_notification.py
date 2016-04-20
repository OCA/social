# -*- coding: utf-8 -*-
# © 2016 Therp BV <http://therp.nl>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
from lxml import etree
from openerp import api, fields, models


class MailNotification(models.Model):
    _inherit = 'mail.notification'

    record = fields.Reference(
        selection=lambda self: [
            (m.model, m.name) for m in self.env['ir.model'].search([])
        ],
        compute='_compute_record')
    record_access_link = fields.Char(compute='_compute_record')

    @api.multi
    def _notify_email(self, message_id, force_send=False, user_signature=True):
        if not self.mapped('message_id.subtype_id.template_id'):
            return super(MailNotification, self)._notify_email(
                message_id, force_send=force_send,
                user_signature=user_signature)
        message_ids = []
        for this in self:
            if not this.mapped('message_id.subtype_id.template_id'):
                super(MailNotification, this)._notify_email(
                    message_id, force_send=force_send,
                    user_signature=user_signature)
                continue
            message = this.message_id
            if not this.get_partners_to_email(message):
                continue
            custom_values = {
                'references': message.parent_id.message_id,
            }
            if message.res_id and hasattr(
                self.env[message.model], 'message_get_email_values'
            ):
                message_values = self.env[message.model].browse(
                    message.res_id
                ).message_get_email_values(message)
                # message_get_email_values is guessed to @api.one
                if message_values and isinstance(message_values, list):
                    message_values = message_values[0]
                custom_values.update(message_values)
            message_id = message.subtype_id.template_id.send_mail(this.id)
            if 'mail_message_id' in custom_values:
                custom_values.pop('mail_message_id')
            self.env['mail.mail'].browse(message_id).write(custom_values)
            message_ids.append(message_id)
        return message_ids or True

    @api.multi
    def _compute_record(self):
        for this in self:
            if not this.message_id.model or not this.message_id.res_id:
                continue
            this.record = self.env[this.message_id.model].browse(
                this.message_id.res_id)
            link_html = self.env['mail.mail']._get_partner_access_link(
                self.env['mail.mail'].new({
                    'notification': True,
                    'mail_message_id': this.message_id.id,
                }),
                this.partner_id
            )
            for a in etree.HTML(link_html).xpath('//a[@href]'):
                this.record_access_link = a.get('href')
