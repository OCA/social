# Copyright 2026 Binhex <https://www.binhex.cloud>
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
        # Everything reached from here answers through a redirect, so the
        # notifications go to the session instead of the bus. See
        # ``social.media.base.mixin._notify_user``.
        SocialAccount = request.env["social.account"].with_context(
            social_media_oauth_callback=True
        )
        try:
            # The request token lives on the wizard, whose credentials are
            # restricted to the system group; the wizard is looked up by
            # ``oauth_token`` and ``create_uid`` inside ``_get_access_token``.
            access_token, access_token_secret = SocialAccount.sudo()._get_access_token(
                kwargs
            )
            if access_token and access_token_secret:
                SocialAccount.create_account_x(
                    access_token, access_token_secret, kwargs
                )
        except Exception:  # noqa: BLE001 - the provider may fail in any way
            SocialAccount._notify_association_failure("X")
            _logger.exception("Error creating the X account")
        return request.redirect(SocialAccount._get_social_dashboard_url())
