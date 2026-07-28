# Copyright 2025 Binhex <https://www.binhex.cloud>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import logging

from odoo import http
from odoo.http import request, route

_logger = logging.getLogger(__name__)


class SocialMediaLinkedin(http.Controller):
    """Endpoints called by LinkedIn: OAuth callback and webhook."""

    @route(
        ["/linkedin/callback"],
        type="http",
        auth="user",
    )
    def social_linkedin(self, access_token=None, code=None, **kwargs):
        SocialAccount = request.env["social.account"]
        try:
            (
                client_id,
                client_secret,
                access_token,
            ) = SocialAccount.get_access_token_linkedin(
                code, request.httprequest.path, kwargs
            )
            SocialAccount.create_account_linkedin(
                client_id, client_secret, access_token
            )
            return request.redirect("/web")
        except Exception as e:
            SocialAccount._consume_linkedin_oauth_wizard(kwargs.get("state", ""))
            # Only through the session: this answer is a redirect that
            # reloads the web client, and a bus notification races with it.
            SocialAccount._notify_user_session(
                SocialAccount._format_user_notification(str(e), media="linkedin")
            )
            _logger.exception("Error in the LinkedIn OAuth callback")
            return request.redirect("/web")

    @route(
        ["/linkedin/webhook"],
        type="http",
        auth="user",
    )
    def social_linkedin_webhook(self, **kwargs):
        _logger.info("WEBHOOK LINKEDIN: %s", sorted(kwargs))
