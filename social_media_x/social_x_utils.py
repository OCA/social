# Copyright 2025 Binhex <https://www.binhex.cloud>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from requests_oauthlib import OAuth1

_URL_X = "https://x.com/"
_URL_OAUTH_X = "https://api.twitter.com/oauth"
_URL_OAUTH2_TOKEN_X = "https://api.twitter.com/oauth2/token"
_URL_RATE_LIMITS_X = "https://docs.x.com/x-api/fundamentals/rate-limits"
_URL_PRICING_X = "https://docs.x.com/x-api/getting-started/pricing"
_NO_PAID_PLAN_REASONS_X = (
    # Returned by the endpoints that report the enrollment of the App.
    "client-not-enrolled",
    # Returned by the API v2 endpoints when the App has no plan, because an
    # App without a plan cannot be attached to a Project either.
    "attached to a project",
)


def _is_app_without_paid_plan(error):
    """Whether X rejected the request because the App has no paid plan.

    X has no single answer for it: some endpoints answer ``403`` with
    ``"reason": "client-not-enrolled"``, while the API v2 ones answer ``403``
    asking for an App attached to a Project. Both mean the same since the
    free tier was removed, as only a paid App can belong to a Project.

    :rtype: bool
    """
    message = str(error).lower()
    return any(reason in message for reason in _NO_PAID_PLAN_REASONS_X)


def _get_oauth(api_key, api_secret, request_access_token=False):
    if request_access_token:
        return OAuth1(
            api_key,
            api_secret,
            request_access_token.get("oauth_token"),
            request_access_token.get("oauth_token_secret"),
        )
    return OAuth1(api_key, api_secret)
