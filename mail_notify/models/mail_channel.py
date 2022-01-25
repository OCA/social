from odoo import  models, api
from pyfcm import FCMNotification
from html2text import html2text

class MailChannel(models.Model):
    _inherit = 'mail.channel'

    @api.multi
    def _notify(self, message):
        res = super(MailChannel, self)._notify(message)
        if self.env['ir.config_parameter'].sudo().get_param('mail_notify.is_fcm_enabled'):
            push_service = FCMNotification(
                api_key=self.env['ir.config_parameter'].sudo().get_param('mail_notify.fcm_server_key'))
            base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url') or ''
            message_values = message.message_format()[0]
            icon = message.author_id and (
                        base_url + ('/web/image/res.partner/' + str(message.author_id.id) + '/image_small')) or (
                               base_url + '/mail/static/src/img/smiley/avatar.jpg')
            web_tokens = (message.sudo().mapped(
                'channel_ids.channel_partner_ids.user_ids') - message.sudo().author_id.user_ids).mapped(
                'token_ids').filtered(lambda t: t.type == 'web').mapped('token')
            action_id = self.env.ref('mail.action_discuss').id

            if web_tokens:
                push_service.notify_multiple_devices(registration_ids=web_tokens,
                                                     message_title=message_values['author_id'][1],
                                                     message_icon=icon,
                                                     click_action=base_url + '/web?#action=' + str(action_id) + '&active_id=' + str(self.id),
                                                     message_body=html2text(message_values['body']))
        return res
