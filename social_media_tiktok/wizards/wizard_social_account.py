# Copyright 2026 Domatix <https://www.domatix.cloud>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import logging
from urllib.parse import urlencode

from odoo import fields, models

from ..social_tiktok_utils import (
    _URL_OAUTH_TIKTOK,
    SCOPE_TIKTOK,
    _get_code_verifier,
    _get_state_token,
)

_logger = logging.getLogger(__name__)


class WizardSocialAccount(models.TransientModel):
    """TikTok steps of the account association wizard."""

    _inherit = "wizard.social.account"

    tiktok_client_key = fields.Char(string="TikTok Client Key")
    tiktok_client_secret = fields.Char(string="TikTok Client Secret")
    tiktok_code_verifier = fields.Char()

    def _get_url_redirect(self):
        if self.media_type == "tiktok":
            return "/social_tiktok/callback"
        return super()._get_url_redirect()

    def _get_csrf_state_token(self):
        if self.media_type == "tiktok":
            return _get_state_token()
        return super()._get_csrf_state_token()

    def _get_url_authorize(self):
        """Build the TikTok authorization URL and redirect the user to it."""
        if self.media_type != "tiktok":
            return super()._get_url_authorize()
        try:
            verifier, challenge = _get_code_verifier()
            self.tiktok_code_verifier = verifier
            self._set_csrf_state_token()
            # The redirect URI must be absolute and identical to the one the
            # token exchange sends, so both sides read it from the same place.
            redirect_uri = self.env["social.account"]._tiktok_redirect_uri()
            params = {
                "client_key": self.tiktok_client_key,
                "response_type": "code",
                "scope": SCOPE_TIKTOK,
                "redirect_uri": redirect_uri,
                "state": self.csrf_state_token,
                "code_challenge": challenge,
                "code_challenge_method": "S256",
            }
            return {
                "type": "ir.actions.act_url",
                "url": f"{_URL_OAUTH_TIKTOK}?{urlencode(params)}",
                "target": "self",
            }
        except Exception as e:
            _logger.error("Error getting the TikTok authorize URL: %s", e)
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
        if self.media_type == "tiktok":
            return self._get_url_authorize()
        return result

    def _update_account(self):
        if self.media_type == "tiktok":
            if self.update_keys or self.update_token:
                return self._get_url_authorize()
            self.account_id._update_account_data()
            return super()._update_account()
        return super()._update_account()
