# Copyright 2026 Domatix <https://www.domatix.cloud>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import secrets

_URL_GRAPH = "https://graph.facebook.com/"
_GRAPH_VERSION = "v26.0"
_URL_OAUTH_FACEBOOK = f"https://www.facebook.com/{_GRAPH_VERSION}/dialog/oauth"

SCOPE_FACEBOOK = ",".join(
    [
        "pages_manage_posts",
        "pages_read_engagement",
        "pages_manage_engagement",
        "pages_show_list",
        "pages_read_user_content",
    ]
)


def _get_state_token():
    return secrets.token_urlsafe(32)
