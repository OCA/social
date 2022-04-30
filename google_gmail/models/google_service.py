# Copyright 2022 Camptocamp SA
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

import requests

from odoo import _, api, models
from odoo.exceptions import UserError

TIMEOUT = 20

GOOGLE_TOKEN_ENDPOINT = "https://accounts.google.com/o/oauth2/token"


class GoogleService(models.TransientModel):
    _inherit = "google.service"

    @api.model
    def _get_access_token(self, refresh_token, service, scope):
        """Fetch the access token thanks to the refresh token."""
        get_param = self.env["ir.config_parameter"].sudo().get_param
        client_id = get_param("google_%s_client_id" % service, default=False)
        client_secret = get_param("google_%s_client_secret" % service, default=False)

        if not client_id or not client_secret:
            raise UserError(_("Google %s is not yet configured.", service.title()))

        if not refresh_token:
            raise UserError(_("The refresh token for authentication is not set."))

        try:
            result = requests.post(
                GOOGLE_TOKEN_ENDPOINT,
                data={
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "refresh_token": refresh_token,
                    "grant_type": "refresh_token",
                    "scope": scope,
                },
                headers={"Content-type": "application/x-www-form-urlencoded"},
                timeout=TIMEOUT,
            )
            result.raise_for_status()
        except requests.HTTPError:
            raise UserError(
                _(
                    "Something went wrong during the token generation. Please request again an authorization code."
                )
            )

        json_result = result.json()

        return json_result.get("access_token"), json_result.get("expires_in")
