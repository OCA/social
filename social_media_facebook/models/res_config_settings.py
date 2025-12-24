# Copyright 2025 Kencove (https://www.kencove.com/)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import logging

from odoo import fields, models

_logger = logging.getLogger(__name__)


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    # === Facebook App Credentials ===
    facebook_app_id = fields.Char(
        string="App ID",
        config_parameter="social_media_base.facebook_app_id",
        help="Facebook App ID for OAuth authentication. Get this from https://developers.facebook.com/apps/",
    )
    facebook_app_secret = fields.Char(
        string="App Secret",
        config_parameter="social_media_base.facebook_app_secret",
        help="Facebook App Secret for OAuth authentication. Keep this confidential!",
    )
    facebook_redirect_uri = fields.Char(
        string="OAuth Redirect URI",
        compute="_compute_facebook_redirect_uri",
        readonly=True,
        help=(
            "Copy this URL to your Facebook App Settings → Products → "
            "Facebook Login → Valid OAuth Redirect URIs"
        ),
    )
    # === Facebook system user token ===
    facebook_system_user_token = fields.Char(
        string="System User Token",
        config_parameter="social_media_base.facebook_system_user_token",
    )

    def action_open_system_user_token_wizard(self):
        return {
            "type": "ir.actions.act_window",
            "name": "System User Token",
            "res_model": "wizard.facebook.system.user",
            "view_mode": "form",
            "target": "new",
        }

    # === Connection method ===
    facebook_connection_method = fields.Selection(
        [
            ("app", "Facebook App (OAuth)"),
            ("system_user", "System User Token"),
        ],
        config_parameter="social_media_base.facebook_connection_method",
        default="",
    )

    use_app_login = fields.Boolean(readonly=True)

    use_system_user = fields.Boolean(readonly=True)

    def get_values(self):
        res = super().get_values()
        param = (
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("social_media_base.facebook_connection_method", default="")
        )
        res.update(
            {
                "use_app_login": param == "app",
                "use_system_user": param == "system_user",
            }
        )
        return res

    # === Facebook Lead Ads Webhook ===
    facebook_webhook_verify_token = fields.Char(
        string="Webhook Verify Token",
        config_parameter="social_media_facebook.webhook_verify_token",
        help=(
            "Custom token for verifying webhook requests from Facebook. "
            "Use a secure random string."
        ),
        default="odoo_facebook_webhook",
    )
    facebook_webhook_url = fields.Char(
        string="Webhook URL",
        compute="_compute_facebook_webhook_url",
        readonly=True,
        help="Copy this URL to your Facebook App Settings → Webhooks → Callback URL",
    )

    def _compute_facebook_redirect_uri(self):
        """Compute the OAuth redirect URI for Facebook"""
        base_url = self.env["ir.config_parameter"].sudo().get_param("web.base.url")
        for record in self:
            record.facebook_redirect_uri = f"{base_url}/facebook/callback"

    def _compute_facebook_webhook_url(self):
        """Compute the webhook URL for Facebook Lead Ads"""
        base_url = self.env["ir.config_parameter"].sudo().get_param("web.base.url")
        for record in self:
            record.facebook_webhook_url = f"{base_url}/facebook/webhook/leads"
