from odoo import models, fields, api
import requests
import logging

_logger = logging.getLogger(__name__)

class MailThread(models.AbstractModel):
    _inherit = 'mail.thread'

    def action_send_whatsapp(self, message):
        """Action to send message via WhatsApp (called from JS)."""
        # Placeholder for WhatsApp send logic
        # Integrate with WhatsApp Business API here
        self.message_post(
            body=message,
            message_type='whatsapp',
            subtype_xmlid='mail_whatsapp_chatter.mt_whatsapp',
        )

    def send_whatsapp_message(self, message_body, partner_id=None):
        """Send message via WhatsApp API and post to chatter."""

        self.ensure_one()

        # If no partner_id provided, try to get from context
        if not partner_id:
            partner_id = self.env.context.get('default_partner_id')
            if not partner_id and hasattr(self, 'partner_id'):
                partner_id = self.partner_id.id

        if not partner_id:
            _logger.warning('No partner found to send WhatsApp message')
            return False

        partner = self.env['res.partner'].browse(partner_id)
        phone = partner.mobile or partner.phone

        if not phone:
            _logger.warning('Partner %s has no phone number for WhatsApp', partner.name)
            return False

        # Get WhatsApp API configuration
        api_url = self.env['ir.config_parameter'].sudo().get_param(
            'whatsapp.api_url',
            'https://graph.instagram.com/v18.0'
        )
        phone_number_id = self.env['ir.config_parameter'].sudo().get_param(
            'whatsapp.phone_number_id'
        )
        api_token = self.env['ir.config_parameter'].sudo().get_param(
            'whatsapp.api_token'
        )

        if not phone_number_id or not api_token:
            _logger.error('WhatsApp API credentials not configured')
            return False

        # Clean phone number (remove non-digits, ensure country code)
        clean_phone = ''.join(c for c in phone if c.isdigit())
        if not clean_phone.startswith('55'):  # Brazil
            clean_phone = '55' + clean_phone.lstrip('0')

        try:
            # Send message via WhatsApp API
            url = f'{api_url}/{phone_number_id}/messages'
            headers = {
                'Authorization': f'Bearer {api_token}',
                'Content-Type': 'application/json'
            }
            payload = {
                'messaging_product': 'whatsapp',
                'recipient_type': 'individual',
                'to': clean_phone,
                'type': 'text',
                'text': {'body': message_body}
            }

            response = requests.post(url, headers=headers, json=payload, timeout=10)

            if response.status_code in [200, 201]:
                response_data = response.json()
                wa_message_id = response_data.get('messages', [{}])[0].get('id', '')

                # Post to chatter with WhatsApp metadata
                mail_message = self.message_post(
                    body=message_body,
                    message_type='comment',
                    subtype_xmlid='mail_whatsapp_chatter.mt_whatsapp',
                )
                mail_message.write({
                    'is_whatsapp': True,
                    'whatsapp_phone': clean_phone,
                    'whatsapp_message_id': wa_message_id,
                })

                _logger.info('WhatsApp message sent to %s (ID: %s)', clean_phone, wa_message_id)
                return True
            else:
                error_msg = response.json().get('error', {}).get('message', response.text)
                _logger.error('WhatsApp API error: %s', error_msg)
                return False

        except Exception as e:
            _logger.error('Error sending WhatsApp message: %s', str(e))
            return False
