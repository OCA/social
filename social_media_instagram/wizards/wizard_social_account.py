# Copyright 2026 Domatix <https://www.domatix.cloud>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import logging
from urllib.parse import urlencode

from odoo import fields, models

from ..social_instagram_utils import (
    _URL_OAUTH_INSTAGRAM,
    SCOPE_INSTAGRAM,
    _get_state_token,
)

_logger = logging.getLogger(__name__)


class WizardSocialAccount(models.TransientModel):
    """Instagram steps of the account association wizard."""

    _inherit = "wizard.social.account"

    instagram_app_id = fields.Char(string="Instagram App ID")
    instagram_app_secret = fields.Char()

    def _get_url_redirect(self):
        if self.media_type == "instagram":
            return "/social_instagram/callback"
        return super()._get_url_redirect()

    def _get_csrf_state_token(self):
        if self.media_type == "instagram":
            return _get_state_token()
        return super()._get_csrf_state_token()

    def _get_url_authorize(self):
        if self.media_type != "instagram":
            return super()._get_url_authorize()
        try:
            self._set_csrf_state_token()
            params = {
                "client_id": self.instagram_app_id,
                "redirect_uri": self.env["social.account"]._instagram_redirect_uri(),
                "response_type": "code",
                "state": self.csrf_state_token,
                "scope": SCOPE_INSTAGRAM,
            }
            return {
                "type": "ir.actions.act_url",
                "url": f"{_URL_OAUTH_INSTAGRAM}?{urlencode(params)}",
                "target": "self",
            }
        except Exception as e:
            _logger.error("Error getting the Instagram authorize URL: %s", e)
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "target": "new",
                "params": {
                    "message": self.env._(
                        "Account access could not be authorized. Please check "
                        "your settings or try again later."
                    ),
                    "type": "danger",
                    "sticky": False,
                    "next": {"type": "ir.actions.act_window_close"},
                },
            }

    def _action_add_account(self):
        result = super()._action_add_account()
        if self.media_type == "instagram":
            return self._get_url_authorize()
        return result

    def _update_account(self):
        if self.media_type == "instagram":
            if self.update_keys or self.update_token:
                return self._get_url_authorize()
            self.account_id._update_account_data()
            return super()._update_account()
        return super()._update_account()
