# Copyright 2025 Binhex <https://www.binhex.cloud>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import logging

from werkzeug.urls import url_encode, url_join

from odoo import _, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

from ..social_facebook_utils import _SCOPE_FACEBOOK_ALL, _URL_AUTH_FACEBOOK


class WizardSocialAccount(models.TransientModel):
    _inherit = "wizard.social.account"

    facebook_app_id = fields.Char(string="App ID")
    facebook_app_secret = fields.Char(string="App Secret")

    def _get_url_redirect(self):
        if self.media_type == "facebook":
            return url_join(self.get_base_url(), "/facebook/callback")
        else:
            return super()._get_url_redirect()

    def _action_add_account(self):
        result = super()._action_add_account()
        context = dict(self.env.context)
        if self.media_type == "facebook":
            _logger.info("=" * 80)
            _logger.info("Wizard: Starting Facebook OAuth flow...")
            _logger.info("Wizard ID: %s", self.id)

            # Use wizard fields (like LinkedIn and X do)
            app_id = self.facebook_app_id
            app_secret = self.facebook_app_secret

            _logger.info("App ID: %s", app_id)
            _logger.info("App Secret configured: %s", bool(app_secret))

            redirect_url = self._get_url_redirect()
            _logger.info("OAuth redirect URL: %s", redirect_url)

            params = {
                "client_id": app_id,
                "redirect_uri": redirect_url,
                "scope": ",".join(_SCOPE_FACEBOOK_ALL),
                "response_type": "code",
            }
            url_auth = f"{_URL_AUTH_FACEBOOK}?{url_encode(params)}"
            _logger.info("Facebook OAuth URL: %s", url_auth[:100] + "...")
            _logger.info("=" * 80)

            if not context.get("only_url", False):
                return {
                    "type": "ir.actions.act_url",
                    "url": url_auth,
                    "target": "self",
                }
            return url_auth
        else:
            return result

    def _action_valid_add_account(self):
        result = super()._action_valid_add_account()
        if self.media_type == "facebook":
            # Validation is handled in Python constraint
            pass
        return result

    def _update_account(self):
        if self.media_type == "facebook":
            if self.update_keys:
                # Update API credentials and re-authenticate
                self.account_id.write(
                    {
                        "facebook_app_id": self.facebook_app_id,
                        "facebook_app_secret": self.facebook_app_secret,
                    }
                )
                return {
                    "type": "ir.actions.act_url",
                    "url": self.with_context(only_url=True)._action_add_account(),
                    "target": "self",
                }
            else:
                # Just refresh account info
                self._notify_user_client(
                    notif_type="social_form_success",
                    notif_message=_("The account was updated successfully"),
                    media="facebook",
                    account_name=self.account_id.name,
                )
        else:
            return super()._update_account()
