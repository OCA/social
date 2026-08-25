# Copyright 2026 Binhex <https://www.binhex.cloud>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import logging

from odoo import _, http
from odoo.exceptions import AccessError, UserError
from odoo.http import request, route

_logger = logging.getLogger(__name__)


class SocialMediaLinkedin(http.Controller):
    """Endpoint called by LinkedIn at the end of the OAuth flow."""

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
            ) = SocialAccount._get_access_token_linkedin(
                code, request.httprequest.path, kwargs
            )
            SocialAccount._create_account_linkedin(
                client_id, client_secret, access_token
            )
            SocialAccount._notify_user_session(
                SocialAccount._format_user_notification(
                    _("The account was associated successfully"),
                    media="linkedin",
                    message_type="success",
                ),
                message_type="success",
            )
            return request.redirect(SocialAccount._get_social_dashboard_url())
        except (AccessError, UserError) as e:
            SocialAccount._consume_linkedin_oauth_wizard(kwargs.get("state", ""))
            # These messages are written for the end user and explain what to
            # do, so they are the only useful feedback of the association flow.
            SocialAccount._notify_user_session(
                SocialAccount._format_user_notification(str(e), media="linkedin")
            )
            _logger.warning("Error in the LinkedIn OAuth callback: %s", e)
            return request.redirect("/web")
        except Exception:  # noqa: BLE001 - the provider may fail in any way
            SocialAccount._consume_linkedin_oauth_wizard(kwargs.get("state", ""))
            # The exception may carry the raw provider response, so the user
            # only gets a generic message and the detail stays in the log.
            SocialAccount._notify_user_session(
                SocialAccount._format_user_notification(
                    _(
                        "The account could not be associated. "
                        "Check the server log for details."
                    ),
                    media="linkedin",
                )
            )
            _logger.exception("Error in the LinkedIn OAuth callback")
            return request.redirect("/web")
