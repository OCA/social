# Copyright 2026 Domatix <https://www.domatix.cloud>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import secrets

_URL_GOOGLE_AUTH = "https://accounts.google.com/o/oauth2/v2/auth"
_URL_GOOGLE_TOKEN = "https://oauth2.googleapis.com/token"
_URL_YOUTUBE_API = "https://www.googleapis.com"

SCOPE_YOUTUBE = " ".join(
    [
        "https://www.googleapis.com/auth/youtube.force-ssl",
        "https://www.googleapis.com/auth/youtube.upload",
    ]
)


def _get_state_token():
    return secrets.token_urlsafe(32)
