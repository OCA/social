from odoo import fields, models

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    is_fcm_enabled = fields.Boolean('Use FCM for Push Notifications', config_parameter='mail_notify.is_fcm_enabled')
    fcm_server_key = fields.Char('Server API Key', config_parameter='mail_notify.fcm_server_key')
    fcm_vapid_key = fields.Char('VAPID Key', config_parameter='mail_notify.fcm_vapid_key')
    fcm_messaging_id = fields.Char('Messaging ID', config_parameter='mail_notify.fcm_messaging_id')
