# Copyright 2020 Creu Blanca
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class MailMessage(models.Model):

    _inherit = 'mail.message'

    telegram_chat_id = fields.Many2one(
        'mail.telegram.chat',
        readonly=True,
        store=True,
        compute='_compute_telegram_chat_id',
    )
    telegram_unread = fields.Boolean(
        default=False,
    )

    @api.depends('telegram_notification_ids')
    def _compute_telegram_chat_id(self):
        for rec in self:
            if rec.telegram_notification_ids:
                rec.telegram_chat_id = rec.telegram_notification_ids[0].chat_id

    @api.model
    def _message_read_dict_postprocess(self, messages, message_tree):
        result = super()._message_read_dict_postprocess(messages, message_tree)
        for message_dict in messages:
            message_id = message_dict.get('id')
            message = message_tree[message_id]
            notifications = message.telegram_notification_ids
            if notifications:
                message_dict.update({
                    'telegram_chat_id': message.telegram_chat_id.id,
                    'telegram_unread': message.telegram_unread,
                    'customer_telegram_status': 'received' if all(
                        d.state == 'received' for d in notifications
                    ) else message_dict['customer_telegram_status'],
                })
        return result

    def set_message_done(self):
        self.write({'telegram_unread': False})
        return super().set_message_done()
