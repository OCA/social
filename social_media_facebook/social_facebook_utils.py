# Copyright 2025 Binhex <https://www.binhex.cloud>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

# Facebook API URLs
_URL_FACEBOOK = "https://www.facebook.com/"
_URL_GRAPH_FACEBOOK = "https://graph.facebook.com/v18.0"
_URL_AUTH_FACEBOOK = "https://www.facebook.com/v18.0/dialog/oauth"

# Facebook API Headers
_HEADERS_FACEBOOK = {
    "Accept": "application/json",
}

# Facebook OAuth Scopes
# Base scopes for all features
_SCOPE_FACEBOOK = [
    "pages_show_list",           # Required: List available pages
    "pages_read_engagement",     # Required: Read post metrics
    "public_profile",            # Required: Basic profile info
]

# Additional scopes enabled by feature
_SCOPE_FACEBOOK_PUBLISHING = [
    "pages_manage_posts",        # Feature #6: Publish content
]

_SCOPE_FACEBOOK_COMMENTS = [
    "pages_read_user_content",   # Feature #4: Read comments
    "pages_manage_engagement",   # Feature #4: Reply to comments
]

_SCOPE_FACEBOOK_LEADS = [
    "leads_retrieval",           # Feature #5: Access lead ads data
]

_SCOPE_FACEBOOK_ADS = [
    "ads_read",                  # Feature #2.2: Read ad insights
]

# Combined default scopes (enable all features)
_SCOPE_FACEBOOK_ALL = (
    _SCOPE_FACEBOOK +
    _SCOPE_FACEBOOK_PUBLISHING +
    _SCOPE_FACEBOOK_COMMENTS +
    _SCOPE_FACEBOOK_LEADS +
    _SCOPE_FACEBOOK_ADS
)
