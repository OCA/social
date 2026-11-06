# Copyright 2026 Domatix <https://www.domatix.cloud>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import base64
import hashlib
import secrets

_URL_OAUTH_TIKTOK = "https://www.tiktok.com/v2/auth/authorize/"
_URL_OAUTH2_TOKEN_TIKTOK = "https://open.tiktokapis.com/v2/oauth/token/"
_URL_TIKTOK_API = "https://open.tiktokapis.com/v2/"

SCOPE_TIKTOK = ",".join(
    [
        "user.info.basic",
        "user.info.profile",
        "user.info.stats",
        "video.publish",
        "video.list",
    ]
)


def _get_state_token():
    """Return a random anti-CSRF state token for the OAuth flow."""
    return secrets.token_urlsafe(32)


def _get_code_verifier():
    """Return a PKCE code verifier and its challenge (RFC 7636)."""
    verifier = secrets.token_urlsafe(64)
    challenge = (
        base64.urlsafe_b64encode(hashlib.sha256(verifier.encode("utf-8")).digest())
        .rstrip(b"=")
        .decode("utf-8")
    )
    return verifier, challenge
