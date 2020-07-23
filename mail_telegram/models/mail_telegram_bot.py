# Copyright 2020 Creu Blanca
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class MailTelegramBot(models.Model):

    _name = 'mail.telegram.bot'
    _description = 'Telegram Bot'

    name = fields.Char(required=True)
    token = fields.Char(required=True)

    _sql_constraints = [
        (
            'mail_telegram_bot_token',
            'unique(token)',
            'Token must be unique'
        ),
    ]
