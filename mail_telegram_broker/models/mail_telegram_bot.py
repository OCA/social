# Copyright 2020 Creu Blanca
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class MailTelegramBot(models.Model):

    _inherit = 'mail.telegram.bot'

    show_on_app = fields.Boolean(default=True)

    @api.model
    def bot_fetch_slot(self):
        result = []
        for record in self.search([('show_on_app', '=', True)]):

            result.append({
                'id': record.id,
                'name': record.name,
                'channel_name': 'telegram_bot_%s' % record.id,
                'threads': [
                    thread._get_thread_data()
                    for thread in self.env['mail.telegram.chat'].search([
                        ('show_on_app', '=', True),
                        ('bot_id', '=', record.id),
                    ])],
            })
        return result

    def chat_search(self, name):
        self.ensure_one()
        domain = [
            ('bot_id', '=', self.id)
        ]
        if name:
            domain += [('name', 'ilike', '%'+name+'%')]
        return self.env['mail.telegram.chat'].search(domain).read(['name'])
