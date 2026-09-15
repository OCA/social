# Copyright 2026 Binhex <https://www.binhex.cloud>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

_URL_X = "https://x.com/"
_URL_OAUTH_X = "https://api.twitter.com/oauth"
_URL_OAUTH2_TOKEN_X = "https://api.twitter.com/oauth2/token"
_URL_RATE_LIMITS_X = "https://docs.x.com/x-api/fundamentals/rate-limits"
_URL_PRICING_X = "https://docs.x.com/x-api/getting-started/pricing"
_NO_PAID_PLAN_REASONS_X = (
    "client-not-enrolled",
    "attached to a project",
)

# What X accepts in a post, checked before publishing so that the user reads
# it on the form instead of in a failed publication. The media are limits of
# the social media, the same for every account. The message is not: X Premium
# raises it from 280 to 25 000 characters and the plan belongs to the account,
# so the limit is resolved by ``social.account._get_x_max_message_length()``
# and never read from here directly.
_MAX_MESSAGE_LENGTH_X = 280
_MAX_MESSAGE_LENGTH_PREMIUM_X = 25000
_MAX_IMAGES_X = 4
_MAX_VIDEOS_X = 1
# The Media API takes WEBP as well, which LinkedIn does not.
_IMAGE_MIMETYPES_X = ("image/jpeg", "image/png", "image/webp", "image/gif")
_VIDEO_MIMETYPES_X = ("video/mp4",)
# Posts a single ``get_tweets`` answers for, which is what X documents for the
# batch read by ids. The refresh of the figures asks in as many calls as the
# publications it was handed need.
_GET_POSTS_MAX_IDS_X = 100

# The only field the refresh of the figures asks for. The identifier always
# travels in the answer, so nothing else is needed to tell the posts apart.
_POST_FIELDS_METRICS_X = ["public_metrics"]

# A GIF is uploaded as an image but carries its own, larger limit.
_MAX_IMAGE_SIZE_X = 5 * 1024 * 1024
_MAX_GIF_SIZE_X = 15 * 1024 * 1024
_MAX_VIDEO_SIZE_X = 512 * 1024 * 1024


def _is_app_without_paid_plan(error):
    """Whether X rejected the request because the App cannot spend.

    X has no single answer for it: some endpoints answer ``403`` with
    ``"reason": "client-not-enrolled"``, while the API v2 ones answer ``403``
    asking for an App attached to a Project. Both mean the same, as the API
    has no free access tier and only an App that can be billed calls it.

    The contract is loose on purpose: anything is accepted and read through
    ``str().lower()``, so a caller hands over whatever it happens to be
    holding — the exception, the ``requests.Response`` or the raw body —
    without having to dig the reason out first. Both wordings travel in the
    body, and every one of those forms carries it.

    :param error: the exception, the response or the body X answered with.
    :return: whether both readings point at the same missing paid plan.
    :rtype: bool
    """
    message = str(error).lower()
    return any(reason in message for reason in _NO_PAID_PLAN_REASONS_X)
