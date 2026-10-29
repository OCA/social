# Copyright 2025 Binhex <https://www.binhex.cloud>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import logging

from odoo import http
from odoo.http import request, route

_logger = logging.getLogger(__name__)


class SocialMediaLinkedin(http.Controller):
    @route(
        ["/linkedin/callback"],
        type="http",
        auth="user",
    )
    def social_linkedin(self, access_token=None, code=None, **kwargs):
        SocialAccount = request.env["social.account"]
        try:
            client_id = None
            client_secret = None
            if not access_token:
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
            # Notifying the user
            SocialAccount._notify_user_client(
                notif_type="social_kanban_danger",
                notif_message=e,
                media="linkedin",
            )
            _logger.error(e)
            return request.redirect("/web")

    @route(
        ["/linkedin/webhook"],
        type="http",
        auth="user",
    )
    def social_linkedin_webhook(self, **kwargs):
        _logger.info(f"WEBHOOK LINKEDIN: {kwargs}")
