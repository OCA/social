# Copyright 2020 Creu Blanca
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class MailTelegramChat(models.Model):
    _name = 'mail.telegram.chat'
    _description = 'Mail Telegram Chat'

    name = fields.Char(required=True)
    active = fields.Boolean(default=True)
    token = fields.Char(required=True)
    chat_id = fields.Char(required=True)
