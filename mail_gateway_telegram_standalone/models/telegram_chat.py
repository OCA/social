from odoo import fields, models


class TelegramChat(models.Model):
    _name = "telegram.chat"
    _description = "Telegram Chat"

    name = fields.Char(
        required=True, help="Friendly name for the chat (e.g. Admin Group)"
    )
    chat_id = fields.Char(required=True, help="Numeric ID from Telegram")
    gateway_id = fields.Many2one(
        "mail.gateway", ondelete="cascade", string="Mail Gateway"
    )
