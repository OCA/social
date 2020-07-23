# Copyright 2020 Creu Blanca
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class MailMessageTelegram(models.Model):
    _inherit = 'mail.message.telegram'

    state = fields.Selection(
        selection_add=[('received', 'Received')],
    )
    chat_id = fields.Many2one(ondelete='cascade')

    @api.model_create_multi
    def create(self, vals_list):
        messages = super().create(vals_list)
        if self.env.context.get('notify_telegram', False):
            notifications = []
            for message in messages:
                notifications.append([
                    (self._cr.dbname,
                     'mail.telegram.bot', message.chat_id.bot_id.id),
                    {'message': message.mail_message_id.message_format()[0]}
                ])
            self.env['bus.bus'].sendmany(notifications)
        return messages
