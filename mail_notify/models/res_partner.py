from odoo import models, api
from pyfcm import FCMNotification
from html2text import html2text

class ResPartner(models.Model):
    _inherit = 'res.partner'

    @api.multi
    def _notify_by_chat(self, message):
        res = super(ResPartner, self)._notify_by_chat(message)
        if self.env['ir.config_parameter'].sudo().get_param('mail_notify.is_fcm_enabled'):
            web_tokens = self.sudo().mapped('user_ids.token_ids').filtered(lambda t: t.type == 'web').mapped('token')
            base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url') or ''
            push_service = FCMNotification(
                api_key=self.env['ir.config_parameter'].sudo().get_param('mail_notify.fcm_server_key'))
            message_values = message.message_format()[0]
            if not message.model and self.env.context.get('default_res_id') and self.env.context.get('default_res_model'):
                message.write({'model': self.env.context.get('default_res_model'), 'res_id': self.env.context.get('default_res_id')})
            if not message.model and self.env.context.get('active_id') and self.env.context.get('active_model'):
                message.write({'model': self.env.context.get('active_model'), 'res_id': self.env.context.get('active_id')})
            icon = message_values.get('module_icon') and message_values.get('module_icon') or \
                   message.author_id and '/web/image/res.partner/' + str(message.author_id.id) + '/image_small' or \
                   '/mail/static/src/img/smiley/avatar.jpg'

            if web_tokens:
                push_service.notify_multiple_devices(registration_ids=web_tokens,
                                                     message_title=message_values['author_id'][1] + ': ' + (message_values['subject'] or message_values['record_name']),
                                                     message_icon=base_url + icon,
                                                     click_action=base_url + '/mail/view?message_id=' + str(message.id),
                                                     message_body=html2text(message_values['body']))
        return res
