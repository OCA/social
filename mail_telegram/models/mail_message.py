# Copyright 2020 Creu Blanca
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class MailMessage(models.Model):
    _inherit = 'mail.message'

    message_type = fields.Selection(selection_add=[('telegram', 'Telegram')])
    telegram_notification_ids = fields.One2many(
        'mail.message.telegram',
        inverse_name='mail_message_id'
    )

    @api.model
    def _message_read_dict_postprocess(self, messages, message_tree):
        result = super()._message_read_dict_postprocess(messages, message_tree)
        for message_dict in messages:
            message_id = message_dict.get('id')
            message = message_tree[message_id]
            if message.telegram_notification_ids:
                notifications = message.telegram_notification_ids
                message_dict.update({
                    'telegram': 1,
                    'customer_telegram_status':
                        (
                            all(d.state == 'sent' for d in notifications) and
                            'sent'
                        ) or (
                            any(d.state == 'exception' for d in notifications)
                            and 'exception'
                        ) or 'ready',
                })
            else:
                message_dict['telegram'] = 0
        return result
