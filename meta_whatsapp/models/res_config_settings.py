from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    meta_api_url = fields.Char(
        string="Meta API URL",
        config_parameter="meta_whatsapp.api_url",
        default="https://graph.facebook.com",
    )
    meta_api_version = fields.Char(
        string="Meta API Version",
        config_parameter="meta_whatsapp.api_version",
        default="v25.0",
    )
    meta_access_token = fields.Char(
        string="Access Token", config_parameter="meta_whatsapp.access_token",
    )
    meta_phone_number_id = fields.Char(
        string="Phone Number ID", config_parameter="meta_whatsapp.phone_number_id",
    )
    meta_waba_id = fields.Char(
        string="WhatsApp Business Account ID", config_parameter="meta_whatsapp.waba_id",
    )

    def action_sync_whatsapp_templates(self):
        """Bridge method to sync templates from settings."""
        return self.env["whatsapp.template"].action_sync_templates()
