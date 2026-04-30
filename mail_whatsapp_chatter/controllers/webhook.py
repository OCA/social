from odoo import http
from odoo.http import request


class WhatsAppWebhook(http.Controller):

    @http.route('/whatsapp/webhook', type='http', auth='public', methods=['GET', 'POST'], csrf=False)
    def webhook(self, **kwargs):
        if request.httprequest.method == 'GET':
            # Verification
            verify_token = request.env['ir.config_parameter'].sudo().get_param('whatsapp.verify_token', 'your_token')
            if kwargs.get('hub.verify_token') == verify_token:
                return kwargs.get('hub.challenge')
            return 'Forbidden', 403
        elif request.httprequest.method == 'POST':
            data = request.jsonrequest
            # Process WhatsApp message
            # Extract phone, message, find record
            phone = data.get('entry', [{}])[0].get('changes', [{}])[0].get('value', {}).get('from')
            message_text = data.get('entry', [{}])[0].get('changes', [{}])[0].get('value', {}).get('text', {}).get('body')
            whatsapp_id = data.get('entry', [{}])[0].get('changes', [{}])[0].get('value', {}).get('messages', [{}])[0].get('id')
            # Find partner/thread by phone and post message
            partner = request.env['res.partner'].sudo().search([('phone', '=ilike', phone)], limit=1)
            if partner:
                partner.message_post(
                    body=message_text,
                    message_type='whatsapp',
                    subtype_xmlid='mail_whatsapp_chatter.mt_whatsapp',
                    whatsapp_phone=phone,
                    whatsapp_message_id=whatsapp_id,
                )
            return 'OK'
