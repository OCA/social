# Copyright 2025 Binhex <https://www.binhex.cloud>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import random
import string
from datetime import date, datetime, timedelta

from werkzeug.urls import url_encode, url_join

from odoo import fields, models
from odoo.tools import hmac

from ..social_linkedin_utils import (
    _SCOPE_LINKEDIN,
    _URL_AUTH_V2_LINKEDIN,
)


class WizardSocialAccount(models.TransientModel):
    _inherit = "wizard.social.account"

    linkedin_client = fields.Char(string="Client ID")
    linkedin_secret = fields.Char(string="Client Secret")
    csrf_state_token = fields.Char()

    def _get_url_redirect(self):
        if self.media_type == "linkedin":
            return url_join(self.get_base_url(), "/linkedin/callback")
        return super()._get_url_redirect()

    def _generate_code(self, length=10):
        caracteres = string.ascii_letters + string.digits
        return "".join(random.choices(caracteres, k=length))

    def _get_csrf_state_token(self):
        if self.media_type == "linkedin":
            return hmac(
                self.env(su=True),
                f"{self.media_type}-account-{self._generate_code()}-csrf-token",
                self.media_id.id,
            )
        else:
            return super()._get_csrf_state_token()

    def _action_add_account(self):
        result = super()._action_add_account()
        context = dict(self.env.context)
        if self.media_type == "linkedin":
            params = {
                "response_type": "code",
                "client_id": self.linkedin_client,
                "redirect_uri": self._get_url_redirect(),
                "state": self.csrf_state_token,
                "scope": " ".join(_SCOPE_LINKEDIN),
            }
            url_aut = f"{_URL_AUTH_V2_LINKEDIN}/authorization?{url_encode(params)}"
            if not context.get("only_url", False):
                return {
                    "type": "ir.actions.act_url",
                    "url": url_aut,
                    "target": "self",
                }
            return url_aut
        return result

    def _action_valid_add_account(self):
        result = super()._action_valid_add_account()
        if self.media_type == "linkedin":
            self.env["social.account"].sudo().unique_account(
                self.linkedin_client, self.linkedin_secret
            )
        else:
            return result

    def _update_account(self):
        if self.media_type == "linkedin":
            if self.update_keys or self.update_token:
                if self.update_keys:
                    self.account_id.write(
                        {
                            "linkedin_client_id": self.linkedin_client,
                            "linkedin_secret": self.linkedin_secret,
                        }
                    )
                    return {
                        "type": "ir.actions.act_url",
                        "url": self.with_context(only_url=True)._action_add_account(),
                        "target": "self",
                    }
                if self.update_token:
                    token = self.account_id._refresh_token()
                    self.account_id.write(
                        {
                            "access_token": token.get("access_token", False),
                            "refresh_access_token": token.get("refresh_token", False),
                            "expire_access_token_date": date.today()
                            + timedelta(days=token.get("expires_in", 0) / 86400),
                            "refresh_token_expires_in": date.today()
                            + timedelta(
                                days=token.get("refresh_token_expires_in", 0) / 86400
                            ),
                        }
                    )
                    # Notifying the user
                    if not self.env.context.get("not_notify", False):
                        self._notify_user_client(
                            notif_type="social_form_success",
                            notif_message=self.env._(
                                "The token was updated successfully"
                            ),
                            media="linkedin",
                            account_name=self.account_id.name,
                        )
            else:
                organizations = self.account_id.get_account_linkedin(
                    self.account_id.access_token
                )

                for organization in organizations:
                    self.account_id.write(
                        {
                            "name": organization.get("localizedName", False),
                            "username": organization.get("vanityName", False),
                            "image_1920": organization.get("logo", False),
                        }
                    )
            self.account_id.write(
                {
                    "last_update_account": datetime.now(),
                }
            )
        else:
            return super()._update_account()
