# Copyright 2026 Domatix <https://www.domatix.cloud>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import secrets

_GRAPH_VERSION = "v23.0"
# Authorization window and short-lived token endpoint of the "Instagram API
# with Instagram Login": the user authorizes Odoo on Instagram itself, without
# going through Facebook.
_URL_OAUTH_INSTAGRAM = "https://www.instagram.com/oauth/authorize"
_URL_TOKEN_INSTAGRAM = "https://api.instagram.com/oauth/access_token"
# Every Graph call of the API (long-lived token, profile, publishing, comments)
# is served from here.
_URL_GRAPH = "https://graph.instagram.com/"

SCOPE_INSTAGRAM = ",".join(
    [
        "instagram_business_basic",
        "instagram_business_content_publish",
        "instagram_business_manage_comments",
        "instagram_business_manage_insights",
    ]
)


def _get_state_token():
    return secrets.token_urlsafe(32)
