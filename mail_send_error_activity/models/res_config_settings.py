from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    activity_on_mail_error = fields.Boolean(
        string="Activity on Error",
        config_parameter="mail_send_error_activity.activity_on_mail_error",
    )
