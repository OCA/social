# Copyright 2025 Binhex <https://www.binhex.cloud>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import logging

import requests
from werkzeug.urls import url_encode

from odoo import fields, models
from odoo.exceptions import ValidationError

from ..social_x_utils import _get_oauth

_logger = logging.getLogger(__name__)


class WizardSocialAccount(models.TransientModel):
    _inherit = "wizard.social.account"

    x_api_key = fields.Char(string="API Key")
    x_api_secret = fields.Char(string="API Secret")
    username = fields.Char(related="account_id.username")
    oauth_token = fields.Char()

    def _get_url_authorize(self):
        try:
            url = "https://api.twitter.com/oauth/request_token"
            auth = _get_oauth(self.x_api_key, self.x_api_secret)
            response = requests.post(url, auth=auth, timeout=10)
            tokens = dict(x.split("=") for x in response.text.split("&"))
            params = {"oauth_token": tokens["oauth_token"]}
            self.oauth_token = tokens["oauth_token"]
            url_aut = f"https://api.twitter.com/oauth/authorize?{url_encode(params)}"
            return {
                "type": "ir.actions.act_url",
                "url": url_aut,
                "target": "self",
            }
        except ValueError as e:
            _logger.error(f"Error get url authorize {e}")
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "target": "new",
                "params": {
                    "message": self.env._(
                        """
                        Account access could not be authorized.
                        Please check your settings or try again later.
                    """
                    ),
                    "type": "danger",
                    "sticky": False,
                    "next": {"type": "ir.actions.act_window_close"},
                },
            }

    def _action_add_account(self):
        result = super()._action_add_account()
        if self.media_type == "x":
            return self._get_url_authorize()
        else:
            return result

    def _action_valid_add_account(self):
        result = super()._action_valid_add_account()
        if self.media_type == "x":
            if (
                self.env["social.account"].search_count(
                    [
                        ("media_type", "=", "x"),
                        ("x_api_key", "=", self.x_api_key),
                        ("x_api_secret", "=", self.x_api_secret),
                    ]
                )
                > 0
            ):
                raise ValidationError(
                    self.env._("An account with that information already exists.")
                )
        return result

    def _update_account(self):
        if self.media_type == "x":
            if self.update_keys or self.update_token:
                return self._get_url_authorize()
            else:
                self.account_id._update_account_data()
                return super()._update_account()
        else:
            return super()._update_account()