# Copyright 2020 Creu Blanca
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class MailTelegramChat(models.Model):

    _inherit = 'mail.telegram.chat'

    message_ids = fields.One2many(
        'mail.message.telegram',
        inverse_name='chat_id',
    )
    mail_message_ids = fields.One2many(
        'mail.message',
        inverse_name='telegram_chat_id',
    )
    last_message_date = fields.Datetime(
        compute='_compute_message_data',
        store=True,
    )
    unread = fields.Integer(
        compute='_compute_message_data',
        store=True,
    )
    token = fields.Char(
        related='bot_id.token',
        store=True,
        required=False,
    )
    show_on_app = fields.Boolean()
    partner_id = fields.Many2one('res.partner')
    message_main_attachment_id = fields.Many2one(
        string="Main Attachment",
        comodel_name='ir.attachment', index=True, copy=False)

    def message_fetch(self, domain=False, limit=30):
        self.ensure_one()
        if not domain:
            domain = []
        return self.env['mail.message'].search([
            ('telegram_chat_id', '=', self.id)
        ] + domain, limit=limit).message_format()

    @api.depends(
        'mail_message_ids', 'mail_message_ids.date',
        'mail_message_ids.telegram_unread')
    def _compute_message_data(self):
        for r in self:
            r.last_message_date = self.env['mail.message'].search([
                ('telegram_chat_id', '=', r.id)
            ], limit=1, order='date DESC').date
            r.unread = self.env['mail.message'].search_count([
                ('telegram_chat_id', '=', r.id),
                ('telegram_unread', '=', True)])

    def _get_thread_data(self):
        return {
            'id': 'telegram_thread_%s' % self.id,
            'res_id': self.id,
            'name': self.name,
            'last_message_date': self.last_message_date,
            'channel_type': 'telegram_thread',
            'unread': self.unread,
            'bot_id': self.bot_id.id,
        }

    def _telegram_message_post_vals(self, body, **kwargs):
        subtype_id = kwargs.get('subtype_id', False)
        if not subtype_id:
            subtype = kwargs.get('subtype') or 'mt_note'
            if '.' not in subtype:
                subtype = 'mail.%s' % subtype
            subtype_id = self.env['ir.model.data'].xmlid_to_res_id(subtype)
        vals = {
            'chat_id': self.id,
            'body': body,
            'subtype_id': subtype_id,
            'message_type': kwargs.get('message_type', 'comment'),
            'model': self._name,
            'res_id': self.id,
        }
        if kwargs.get('author_id', False):
            vals['author_id'] = kwargs['author_id']
        if 'date' in kwargs:
            vals['date'] = kwargs['date']
        if 'message_id' in kwargs:
            vals['message_id'] = kwargs['message_id']
        vals['telegram_unread'] = kwargs.get('telegram_unread', False)
        vals['attachment_ids'] = []
        for name, content, mimetype in kwargs.get('attachments', []):
            vals['attachment_ids'].append((0, 0, {
                'name': name,
                'datas': content.encode('utf-8'),
                'type': 'binary',
                'datas_fname': name,
                'description': name,
                'mimetype': mimetype,
            }))
        return vals

    @api.returns('mail.telegram.message', lambda value: value.id)
    def telegram_message_post_broker(self, body=False, **kwargs):
        self.ensure_one()
        if not body and not kwargs.get('attachments'):
            return False
        vals = self._telegram_message_post_vals(
            body, telegram_unread=True, author_id=self.partner_id.id, **kwargs)
        vals['state'] = 'received'
        return self.env['mail.message.telegram'].create(vals)

    @api.model_create_multi
    def create(self, vals_list):
        chats = super().create(vals_list)
        notifications = []
        for chat in chats:
            if chat.show_on_app and chat.bot_id.show_on_app:
                notifications.append((
                    (self._cr.dbname, 'mail.telegram.bot', chat.bot_id.id),
                    {'thread': chat._get_thread_data()}
                ))
        if notifications:
            self.env['bus.bus'].sendmany(notifications)
        return chats

    @api.multi
    @api.returns('mail.telegram.message', lambda value: value.id)
    def telegram_message_post(self, body=False, **kwargs):
        self.ensure_one()
        if not body:
            return
        message = self.with_context(
            do_not_notify=True
        ).env['mail.message.telegram'].create(
            self._telegram_message_post_vals(body, **kwargs)
        )
        message.send()
        self.env['bus.bus'].sendone(
            (self._cr.dbname, 'mail.telegram.bot', message.chat_id.bot_id.id),
            {'message': message.mail_message_id.message_format()[0]}
        )
        return message
