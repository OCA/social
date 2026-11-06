# Copyright 2026 Domatix <https://www.domatix.cloud>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import logging
from urllib.parse import urlencode

from odoo import fields, models

from ..social_youtube_utils import (
    _URL_GOOGLE_AUTH,
    SCOPE_YOUTUBE,
    _get_state_token,
)

_logger = logging.getLogger(__name__)


class WizardSocialAccount(models.TransientModel):
    """YouTube steps of the account association wizard."""

    _inherit = "wizard.social.account"

    youtube_client_id = fields.Char(string="YouTube Client ID")
    youtube_client_secret = fields.Char(string="YouTube Client Secret")

    def _get_url_redirect(self):
        if self.media_type == "youtube":
            return "/social_youtube/callback"
        return super()._get_url_redirect()

    def _get_csrf_state_token(self):
        if self.media_type == "youtube":
            return _get_state_token()
        return super()._get_csrf_state_token()

    def _get_url_authorize(self):
        if self.media_type != "youtube":
            return super()._get_url_authorize()
        try:
            self._set_csrf_state_token()
            params = {
                "client_id": self.youtube_client_id,
                "redirect_uri": self.env["social.account"]._youtube_redirect_uri(),
                "response_type": "code",
                "scope": SCOPE_YOUTUBE,
                "access_type": "offline",
                "prompt": "consent",
                "state": self.csrf_state_token,
            }
            return {
                "type": "ir.actions.act_url",
                "url": f"{_URL_GOOGLE_AUTH}?{urlencode(params)}",
                "target": "self",
            }
        except Exception as e:
            _logger.error("Error getting the YouTube authorize URL: %s", e)
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
        if self.media_type == "youtube":
            return self._get_url_authorize()
        return result

    def _update_account(self):
        if self.media_type == "youtube":
            if self.update_keys or self.update_token:
                return self._get_url_authorize()
            self.account_id._update_account_data()
            return super()._update_account()
        return super()._update_account()
