# Copyright 2025 Binhex <https://www.binhex.cloud>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import logging

from odoo import http
from odoo.http import request, route

_logger = logging.getLogger(__name__)


class SocialMediaX(http.Controller):
    """Endpoint called by X to close the OAuth 1.0a flow."""

    @route(
        ["/social_x/callback"],
        type="http",
        auth="user",
    )
    def social_x(self, **kwargs):
        SocialAccount = request.env["social.account"]
        try:
            access_token, access_token_secret = SocialAccount.sudo()._get_access_token(
                kwargs
            )
            if access_token and access_token_secret:
                SocialAccount.create_account_x(
                    access_token, access_token_secret, kwargs
                )
        except Exception as e:
            # Only through the session: this answer is a redirect that
            # reloads the web client, and a bus notification races with it.
            SocialAccount._notify_user_session(
                SocialAccount._format_user_notification(str(e), media="X")
            )
            _logger.exception("Error creating the X account")
        return request.redirect(SocialAccount._get_social_dashboard_url())
