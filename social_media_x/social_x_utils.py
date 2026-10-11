# Copyright 2025 Binhex <https://www.binhex.cloud>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import base64
import hashlib
import os

from requests_oauthlib import OAuth1

_URL_REST_X = "https://api.x.com"
_URL_V2_X = "https://api.x.com/2"

_SCOPES_X = [
    "tweet.read",
    "tweet.write",
    "tweet.read",
    "offline.access",
]


def _get_oauth(api_key, api_secret, request_access_token=False):
    if request_access_token:
        return OAuth1(
            api_key,
            api_secret,
            request_access_token.get("oauth_token"),
            request_access_token.get("oauth_token_secret"),
        )
    return OAuth1(api_key, api_secret)


def _get_code_challenge():
    code_verifier = base64.urlsafe_b64encode(os.urandom(32)).decode("utf-8").rstrip("=")
    code_challenge = hashlib.sha256(code_verifier.encode("utf-8")).digest()
    code_challenge = (
        base64.urlsafe_b64encode(code_challenge).decode("utf-8").rstrip("=")
    )
    return code_challenge
