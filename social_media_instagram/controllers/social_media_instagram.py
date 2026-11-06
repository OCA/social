# Copyright 2026 Domatix <https://www.domatix.cloud>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import logging

from odoo import http
from odoo.http import request, route

from odoo.addons.social_media_base.tools import is_media_request_valid

_logger = logging.getLogger(__name__)


class SocialMediaInstagram(http.Controller):
    """Endpoint called by Instagram to close the OAuth flow."""

    @route(
        ["/social_instagram/callback"],
        type="http",
        auth="user",
    )
    def social_instagram(self, code=None, state=None, error=None, **kwargs):
        SocialAccount = request.env["social.account"]
        if error:
            SocialAccount._notify_user_session(
                SocialAccount._format_user_notification(error, media="Instagram")
            )
            return request.redirect(SocialAccount._get_social_dashboard_url())
        try:
            (
                app_id,
                app_secret,
                access_token,
                expires_in,
            ) = SocialAccount.sudo().get_access_token_instagram(code, state)
            if access_token:
                SocialAccount.sudo().create_instagram_accounts(
                    app_id, app_secret, access_token, expires_in
                )
                SocialAccount._consume_instagram_oauth_wizard(state or "")
        except Exception as e:
            SocialAccount._consume_instagram_oauth_wizard(state or "")
            SocialAccount._notify_user_session(
                SocialAccount._format_user_notification(str(e), media="Instagram")
            )
            _logger.exception("Error creating the Instagram account")
        return request.redirect(SocialAccount._get_social_dashboard_url())

    @route(
        ["/social_instagram/get_image/<int:image_id>"],
        type="http",
        auth="public",
    )
    def social_instagram_get_image(self, image_id, token=None):
        image = request.env["ir.attachment"].sudo().browse(image_id)
        if not is_media_request_valid(request.env, image, token):
            raise request.not_found()
        return (
            request.env["ir.binary"]
            ._get_image_stream_from(image, default_mimetype="image/jpeg")
            .get_response()
        )

    @route(
        ["/social_instagram/get_video/<int:video_id>"],
        type="http",
        auth="public",
    )
    def social_instagram_get_video(self, video_id, token=None):
        video = request.env["ir.attachment"].sudo().browse(video_id)
        if not is_media_request_valid(request.env, video, token):
            raise request.not_found()
        return (
            request.env["ir.binary"]
            ._get_stream_from(video, default_mimetype="video/mp4")
            .get_response()
        )
