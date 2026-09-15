# Copyright 2026 Binhex <https://www.binhex.cloud>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import secrets
from urllib.parse import urlencode, urljoin

from odoo import _, fields, models

from ..social_linkedin_utils import _URL_AUTH_V2_LINKEDIN


class WizardSocialAccount(models.TransientModel):
    """LinkedIn steps of the account association wizard."""

    _inherit = "wizard.social.account"

    linkedin_client = fields.Char(string="Client ID")
    linkedin_secret = fields.Char(string="Client Secret")

    def _get_url_redirect(self):
        if self.media_type == "linkedin":
            return urljoin(self.get_base_url(), "/linkedin/callback")
        else:
            return super()._get_url_redirect()

    def _get_csrf_state_token(self):
        """Return the anti-CSRF state token LinkedIn echoes back.

        The token is opaque and only ever compared for equality against the
        one stored on the wizard, so what it has to be is unguessable, not
        derivable: a random string covers it without a secret to keep.
        """
        if self.media_type == "linkedin":
            return secrets.token_urlsafe(32)
        else:
            return super()._get_csrf_state_token()

    def _action_add_account(self):
        result = super()._action_add_account()
        context = dict(self.env.context)
        if self.media_type == "linkedin":
            # An account being authorized again asks for what the installed
            # modules need and for its own scopes, which is how a module
            # installed, or a product enabled on LinkedIn, after the account
            # was associated reaches the authorization. LinkedIn separates
            # them with spaces; the comma is only how they are stored.
            scopes = (
                self.account_id._get_linkedin_authorization_scopes()
                if self.account_id
                else self.media_id._get_linkedin_scopes()
            )
            params = {
                "response_type": "code",
                "client_id": self.linkedin_client,
                "redirect_uri": self._get_url_redirect(),
                "state": self.csrf_state_token,
                "scope": " ".join(scopes),
            }
            url_aut = f"{_URL_AUTH_V2_LINKEDIN}/authorization?{urlencode(params)}"
            if not context.get("only_url", False):
                return {
                    "type": "ir.actions.act_url",
                    "url": url_aut,
                    "target": "self",
                }
            return url_aut
        else:
            return result

    def _action_valid_add_account(self):
        result = super()._action_valid_add_account()
        if self.media_type == "linkedin":
            self.env["social.account"].sudo()._unique_account(
                self.linkedin_client, self.linkedin_secret
            )
        return result

    def _update_account(self):
        if self.media_type == "linkedin":
            if self.update_keys or self.update_token:
                if self.update_keys:
                    self.account_id.sudo()._unique_account(
                        self.linkedin_client, self.linkedin_secret
                    )
                    return {
                        "type": "ir.actions.act_url",
                        "url": self.with_context(only_url=True)._action_add_account(),
                        "target": "self",
                    }
                if self.update_token:
                    self.account_id._linkedin_store_refreshed_token()
                    if not self.env.context.get("not_notify", False):
                        self._notify_user_client(
                            notif_type="social_form_success",
                            notif_message=_("The token was updated successfully"),
                            media="linkedin",
                            account_name=self.account_id.name,
                        )
            else:
                organizations = self.account_id._get_account_linkedin(
                    self.account_id.sudo().access_token
                )

                # The account is a single one, so LinkedIn only answers with
                # the organization it administers.
                if organizations:
                    organization = organizations[0]
                    self.account_id.write(
                        {
                            "name": organization.get("localizedName", False),
                            "username": organization.get("vanityName", False),
                            "image_1920": organization.get("logo", False),
                        }
                    )
            self.account_id.write(
                {
                    "last_update_account": fields.Datetime.now(),
                }
            )
        else:
            return super()._update_account()
