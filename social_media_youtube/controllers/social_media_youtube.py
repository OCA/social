# Copyright 2026 Domatix <https://www.domatix.cloud>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import logging

from odoo import http
from odoo.http import request, route

_logger = logging.getLogger(__name__)


class SocialMediaYouTube(http.Controller):
    """Endpoint called by Google to close the OAuth flow."""

    @route(
        ["/social_youtube/callback"],
        type="http",
        auth="user",
    )
    def social_youtube(self, code=None, state=None, error=None, **kwargs):
        SocialAccount = request.env["social.account"]
        if error:
            SocialAccount._notify_user_session(
                SocialAccount._format_user_notification(error, media="YouTube")
            )
            return request.redirect(SocialAccount._get_social_dashboard_url())
        try:
            (
                client_id,
                client_secret,
                tokens,
            ) = SocialAccount.sudo().get_access_token_youtube(code, state)
            if tokens:
                SocialAccount.sudo().create_youtube_account(
                    client_id, client_secret, tokens
                )
                SocialAccount._consume_youtube_oauth_wizard(state or "")
        except Exception as e:
            SocialAccount._consume_youtube_oauth_wizard(state or "")
            SocialAccount._notify_user_session(
                SocialAccount._format_user_notification(str(e), media="YouTube")
            )
            _logger.exception("Error creating the YouTube account")
        return request.redirect(SocialAccount._get_social_dashboard_url())
