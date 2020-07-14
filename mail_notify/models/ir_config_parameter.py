from odoo.models import api, Model
from odoo.tools.safe_eval import const_eval

class IrConfigParameter(Model):
    _inherit = "ir.config_parameter"

    @api.model
    def get_fcm_config(self):
        get_param = self.sudo().get_param
        return {
            'is_fcm_enabled': const_eval(get_param("mail_notify.is_fcm_enabled", 'False')),
            'fcm_server_key': get_param("mail_notify.fcm_server_key", 'False'),
            'fcm_vapid_key': get_param("mail_notify.fcm_vapid_key", 'False'),
            'fcm_messaging_id': get_param("mail_notify.fcm_messaging_id", 'False')
        }
