# Copyright 2026 Domatix <https://www.domatix.cloud>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import logging

from odoo import http
from odoo.http import request, route

_logger = logging.getLogger(__name__)


class SocialMediaTikTok(http.Controller):
    """Endpoint called by TikTok to close the OAuth 2.0 flow."""

    @route(
        ["/social_tiktok/callback"],
        type="http",
        auth="user",
    )
    def social_tiktok(self, code=None, state=None, error=None, **kwargs):
        SocialAccount = request.env["social.account"]
        if error:
            SocialAccount._notify_user_session(
                SocialAccount._format_user_notification(error, media="TikTok")
            )
            return request.redirect(SocialAccount._get_social_dashboard_url())
        try:
            (
                client_key,
                client_secret,
                tokens,
            ) = SocialAccount.sudo().get_access_token_tiktok(code, state)
            if tokens:
                SocialAccount.sudo().create_account_tiktok(
                    client_key, client_secret, tokens
                )
                SocialAccount._consume_tiktok_oauth_wizard(state or "")
        except Exception as e:
            SocialAccount._consume_tiktok_oauth_wizard(state or "")
            SocialAccount._notify_user_session(
                SocialAccount._format_user_notification(str(e), media="TikTok")
            )
            _logger.exception("Error creating the TikTok account")
        return request.redirect(SocialAccount._get_social_dashboard_url())
