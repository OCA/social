from odoo import api, fields, models


class MailMessage(models.Model):
    _inherit = 'mail.message'

    is_whatsapp = fields.Boolean(
        'WhatsApp Message',
        compute='_compute_is_whatsapp',
        store=True,
    )
    whatsapp_phone = fields.Char('WhatsApp Phone')
    whatsapp_message_id = fields.Char('WhatsApp Message ID')

    @api.depends('subtype_id')
    def _compute_is_whatsapp(self):
        for message in self:
            message.is_whatsapp = bool(message.subtype_id and message.subtype_id.res_model == 'whatsapp.message')
