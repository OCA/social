# Copyright 2026 Binhex <https://www.binhex.cloud>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import logging
from urllib.parse import parse_qsl, urlencode

import requests
from requests_oauthlib import OAuth1

from odoo import _, fields, models

from ..social_x_utils import (
    _URL_OAUTH_X,
    _URL_PRICING_X,
    _is_app_without_paid_plan,
)

_logger = logging.getLogger(__name__)


class WizardSocialAccount(models.TransientModel):
    """X steps of the account association wizard."""

    _inherit = "wizard.social.account"

    x_api_key = fields.Char(
        string="API Key",
        help=(
            "The API Key of the developer App, which the X Developer Console "
            "lists under OAuth 1.0 Keys as the Consumer Key. Regenerating it "
            "in the Console invalidates the one stored here."
        ),
    )
    x_api_secret = fields.Char(
        string="API Secret",
        help=(
            "The API Key Secret of the developer App, shown by the X Developer "
            "Console only when the Consumer Key is generated. Regenerating it "
            "in the Console invalidates the one stored here."
        ),
    )
    oauth_token = fields.Char()

    def _get_url_authorize(self):
        """Ask X for a request token and redirect the user to authorize it."""
        try:
            url = f"{_URL_OAUTH_X}/request_token"
            auth = OAuth1(self.x_api_key, self.x_api_secret)
            response = requests.post(url, auth=auth, timeout=10)
            if response.status_code != 200:
                # The body is kept as the message because it is what tells a
                # plain rejection apart from an App without a paid plan.
                raise requests.HTTPError(response.text, response=response)
            tokens = dict(parse_qsl(response.text))
            params = {"oauth_token": tokens["oauth_token"]}
            self.oauth_token = tokens["oauth_token"]
            url_aut = f"{_URL_OAUTH_X}/authorize?{urlencode(params)}"
            return {
                "type": "ir.actions.act_url",
                "url": url_aut,
                "target": "self",
            }
        except (ValueError, KeyError, requests.RequestException) as e:
            _logger.error("Error getting the X authorize URL: %s", e)
            links = []
            if _is_app_without_paid_plan(e):
                message = self.env["social.account"]._x_error_message(
                    e, pricing_link="%s"
                )
                links = [{"url": _URL_PRICING_X, "label": _("X API pricing")}]
            else:
                message = _(
                    "Account access could not be authorized. Please check "
                    "your settings or try again later."
                )
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "target": "new",
                "params": {
                    "message": message,
                    "links": links,
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
            self.env["social.account"]._check_unique_credentials(
                [
                    ("media_type", "=", "x"),
                    ("x_api_key", "=", self.x_api_key),
                    ("x_api_secret", "=", self.x_api_secret),
                ],
                _("An account with that information already exists."),
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
