# Copyright 2026 Binhex <https://www.binhex.cloud>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import json
from datetime import timezone
from urllib.parse import quote

from odoo import fields

_URL_FEED_UPDATE_LINKEDIN = "https://www.linkedin.com/feed/update/"
_URL_REST_LINKEDIN = "https://api.linkedin.com/rest"
_URL_V2_LINKEDIN = "https://api.linkedin.com/v2"
_URL_AUTH_V2_LINKEDIN = "https://www.linkedin.com/oauth/v2"

# The value of the ``LinkedIn-Version`` header every REST call carries, in
# the ``YYYYMM`` format LinkedIn dates its versions with. Moving the whole
# connector onto a newer version of the API is changing this line: every
# endpoint is versioned by the header, not by the URL.
_VERSION_STRING_LINKEDIN = "202607"

# Months of history asked for when the time series of an account is first
# filled. The analytics endpoints keep about a year, so asking for more adds
# empty buckets and nothing else. How much of it LinkedIn really serves by
# day is its own decision, so whatever comes back is what gets written.
_STATISTICS_HISTORY_MONTHS_LINKEDIN = 12

_HEADERS_LINKEDIN = {
    "X-Restli-Protocol-Version": "2.0.0",
    "LinkedIn-Version": _VERSION_STRING_LINKEDIN,
}

# The permissions asked for when authorizing an account. Every one of them
# has to be granted by the products enabled on the LinkedIn App, or the
# authorization comes back without it and the calls that need it fail one by
# one instead of failing at association time. Refreshing a token keeps the
# scopes it was issued with, so widening this list only reaches the accounts
# authorized again from scratch.
_SCOPE_LINKEDIN = [
    "profile",
    "r_organization_social",
    "rw_organization_admin",
    "w_member_social",
    "w_organization_social",
    "r_basicprofile",
    "r_organization_admin",
    "email",
    "r_1st_connections_size",
]

# The formats the media APIs of LinkedIn take. Images API: "JPG, GIF, and PNG
# formats". Videos API: "File format: MP4".
_IMAGE_MIMETYPES_LINKEDIN = ("image/jpeg", "image/png", "image/gif")
_VIDEO_MIMETYPES_LINKEDIN = ("video/mp4",)

# What LinkedIn accepts in a post, checked before publishing so that the user
# reads it on the form instead of in a failed publication. They are limits of
# the social media, not of the account: see the ROADMAP of social_media_base.
_MAX_MESSAGE_LENGTH_LINKEDIN = 3000
_MAX_IMAGES_LINKEDIN = 20
_MAX_VIDEOS_LINKEDIN = 1
_MAX_IMAGE_SIZE_LINKEDIN = 10 * 1024 * 1024
_MAX_VIDEO_SIZE_LINKEDIN = 500 * 1024 * 1024

_URN_ORGANIZATION_LINKEDIN = "urn:li:organization:"
_URN_IMAGE_LINKEDIN = "urn:li:image:"
_URN_VIDEO_LINKEDIN = "urn:li:video:"
_URN_SHARE_LINKEDIN = "urn:li:share:"
_URN_UGC_POST_LINKEDIN = "urn:li:ugcPost:"
# A comment is addressed by a composite URN, the thread it lives on plus its
# own identifier: urn:li:comment:(urn:li:activity:6666,120381273128).
_URN_COMMENT_LINKEDIN = "urn:li:comment:"

# The criteria of the organization finder, which the endpoints answering a
# single entity by URN do not take.
_FINDER_PARAMS_LINKEDIN = ("q", "organizationalEntity")

# Days of daily buckets the check for updates watches. The window has to be
# wider than the interval of the cron so a bucket is compared against itself at
# least once before ageing out of it, and wide enough to still catch a figure
# LinkedIn revises a few days late.
_UPDATE_CHECK_DAYS_LINKEDIN = 7

# Which figures of a daily bucket are watched, by their position in the tuple
# ``_get_linkedin_daily_statistics`` builds: clicks, likes, comments, shares
# and impressions. The engagement (position 4) is left out on purpose: it is a
# ratio of the other figures over the impressions, so it cannot move without
# one of them moving, and it is the only float of the set.
_UPDATE_CHECK_FIGURES_LINKEDIN = (0, 1, 2, 3, 5)

# 4 MiB, the size of the parts the Videos API splits an upload into. It is
# only the default: the initialization answers the part boundaries it wants,
# and those are the ones actually used.
_VIDEO_UPLOAD_PART_SIZE_LINKEDIN = 4 * 1024 * 1024

# The Posts API answers at most 100 posts per page, and it may answer fewer
# than asked while there are still posts left, so a page is only the last one
# when it comes back empty. The number of pages is capped to keep a feed that
# never ends from looping forever.
_POSTS_PAGE_SIZE_LINKEDIN = 100
_POSTS_MAX_PAGES_LINKEDIN = 50

# LinkedIn answers 414 to a query string longer than 4 KB, and the statistics
# endpoints take the URN of every post in it. Neither of them paginates, so
# the URNs are the only thing that can be split. The margin covers the rest of
# the query string and what percent-encoding adds to the URNs.
_QUERY_STRING_MAX_BYTES_LINKEDIN = 4096
_QUERY_STRING_MARGIN_BYTES_LINKEDIN = 512

# LinkedIn caps every BATCH_GET at 100 elements (/images, /videos, /posts,
# /creatives, /inMailContents and /conversationAds). The byte-size cut above
# does not cover this path, so the count is capped on its own.
_BATCH_GET_MAX_IDS_LINKEDIN = 100

# How many days before its expiry date a token is treated as expired. The
# check runs before every publication and on the schedule of the updates
# cron, and a token renewed at the last moment is one that a post planned
# for the weekend would not find.
_TOKEN_MARGIN_DAYS_LINKEDIN = 7

# How long to wait for LinkedIn to finish processing an uploaded video:
# ``_VIDEO_POLL_ATTEMPTS_LINKEDIN`` polls, ``_VIDEO_POLL_DELAY_LINKEDIN``
# seconds apart, so their product is the ceiling — a minute here. Both are
# the defaults of an ``ir.config_parameter``, so a slow account can be given
# more without touching the code.
_VIDEO_POLL_ATTEMPTS_LINKEDIN = 30
_VIDEO_POLL_DELAY_LINKEDIN = 2

# LinkedIn answers an error in two dialects and both have to be read. The
# OAuth endpoint speaks ``error`` / ``error_description``; the Rest.li API
# speaks ``serviceErrorCode`` / ``message``. Each tuple is tried in order,
# the OAuth form first, because that is the one that arrives while there is
# still no usable token to blame.
_ERROR_DETAIL_KEYS_LINKEDIN = ("error_description", "message")
_ERROR_CODE_KEYS_LINKEDIN = ("error", "serviceErrorCode")
# Where a validation error keeps its per-field explanations. The two branches
# are read because LinkedIn splits them: what a field got wrong on its own
# goes in ``inputErrors``, what it got wrong given another field's value goes
# in ``conditionalInputErrors``, and either one alone tells half the story.
_ERROR_INPUT_KEYS_LINKEDIN = ("inputErrors", "conditionalInputErrors")

# The codes that mean LinkedIn refused the authorization rather than the
# request. This is the list with the most consequences of the file: a code in
# it becomes a ``SocialCredentialsError``, which is the one failure the
# publication retries on the spot after refreshing the token, and the one
# that flags the account as needing to be authorized again.
_ERROR_CREDENTIALS_CODES_LINKEDIN = (
    "invalid_client",
    "invalid_grant",
    "invalid_request",
    "invalid_token",
    "REVOKED_ACCESS_TOKEN",
    "EXPIRED_ACCESS_TOKEN",
)


def social_url_encode(param_field, params_values):
    """Encode one query parameter the way the social media APIs expect it.

    ``urlencode`` is not enough because those APIs read a list as
    ``List(a,b,c)`` and refuse the percent-encoded parentheses and commas.

    The colon is the subtle one, and it goes both ways. Rest.li reads a
    query parameter as a structure, so a raw ``:`` is a field separator:
    a struct such as ``(timeRange:(start:1,end:2))`` needs its colons
    untouched, while a URN such as ``urn:li:organization:123`` is an opaque
    string whose colons have to travel escaped or the API answers
    ``ILLEGAL_ARGUMENT``. A value that opens with a parenthesis is a
    struct; anything else is opaque.

    :param str param_field: the key of ``params_values`` being encoded.
    :param dict params_values: the whole set of parameter values.
    :rtype: str
    """
    value = params_values[param_field]
    if isinstance(value, list):
        # The commas separate the elements of the list, so they stay raw.
        inner = ",".join(quote(str(item), safe=",") for item in value)
        return f"{param_field}=List({inner})"
    value = str(value)
    if value.startswith("("):
        return f"{param_field}={quote(value, safe='(),:')}"
    return f"{param_field}={quote(value, safe=',')}"


def _encoded_urns_bytes(urns, param_field):
    """Return what the URNs weigh in a query string, once encoded.

    Measured through the very function that builds the parameter, so the
    ``List(...)`` wrapper and the percent-encoding are counted as they will
    be sent.

    :param urns: the URNs of one batch.
    :param param_field: the name of the query parameter carrying them.
    :rtype: int
    """
    encoded = social_url_encode(param_field, {param_field: [",".join(urns)]})
    return len(encoded.encode())


def _batch_urns_by_url_size(urns, param_field, fixed_query_bytes=0):
    """Split the URNs into batches whose query string LinkedIn accepts.

    The statistics endpoints take every URN in the query string and none of
    them paginates, so a feed of more than about a hundred posts can only be
    read in several calls. The cut is made on the encoded size rather than on
    a fixed number of URNs because their length varies and the encoding does
    not grow linearly with it.

    Not ``odoo.tools.misc.split_every``: that one cuts by count and cannot
    express a budget in bytes, which is the whole point here.

    A URN too long to fit on its own is still given its own batch: LinkedIn
    refusing one call is better than never making it.

    :param urns: the URNs to split, in the order they should be asked for.
    :param param_field: the name of the query parameter carrying them.
    :param fixed_query_bytes: what the rest of the query string weighs.
    :return: the batches of URNs, empty when there is nothing to ask for.
    :rtype: list
    """
    budget = (
        _QUERY_STRING_MAX_BYTES_LINKEDIN
        - _QUERY_STRING_MARGIN_BYTES_LINKEDIN
        - fixed_query_bytes
    )
    batches = []
    batch = []
    for urn in urns:
        if batch and _encoded_urns_bytes(batch + [urn], param_field) > budget:
            batches.append(batch)
            batch = [urn]
        else:
            batch.append(urn)
    if batch:
        batches.append(batch)
    return batches


def _linkedin_error_inputs(payload):
    """Return the per-field explanations of a LinkedIn validation error.

    A validation error keeps its explanations in ``errorDetails`` and not in
    ``message``, which only says that something did not validate. Reading
    ``message`` alone would tell the user a post was rejected without ever
    saying which field LinkedIn refused.

    An ``errorDetails`` that is not a dict is ignored without a word: it is
    the shape of an error that is not a validation error at all, and the
    caller already falls back to the plain message for those.

    :param dict payload: the parsed answer of LinkedIn.
    :return: one description per rejected field, in the order LinkedIn
        reported them.
    :rtype: list
    """
    details = payload.get("errorDetails")
    if not isinstance(details, dict):
        return []
    descriptions = []
    for key in _ERROR_INPUT_KEYS_LINKEDIN:
        for input_error in details.get(key) or []:
            description = isinstance(input_error, dict) and input_error.get(
                "description"
            )
            if description:
                descriptions.append(str(description))
    return descriptions


def _linkedin_error_payload(error):
    """Return the answer of LinkedIn as a dict, when it is one.

    Three shapes arrive here and that is why all three are handled.
    ``_request_linkedin`` answers the parsed body on a 200 and the raw
    ``requests.Response`` on anything else, so a caller reporting a failure
    holds one or the other; and an exception raised further down carries the
    JSON of LinkedIn inside ``str(error)``. Reading ``text`` first and
    falling back to ``str`` covers the three without asking which one it is.

    :param error: a ``requests.Response``, an already parsed body, or
        anything raised while talking to LinkedIn.
    :return: the parsed body, or an empty dict when it is not JSON.
    :rtype: dict
    """
    if isinstance(error, dict):
        return error
    body = getattr(error, "text", None)
    if body is None:
        body = str(error)
    try:
        payload = json.loads(body)
    except (TypeError, ValueError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _linkedin_error_detail(error):
    """Return what LinkedIn answered, in a readable form.

    A validation error is reported field by field, since its ``message``
    only says that something failed. The answer of LinkedIn is never
    dropped: when it carries no known key, or when it is not JSON at all,
    its body is returned as it is.

    :param error: polymorphic, the same three shapes
        ``_linkedin_error_payload`` reads — a ``requests.Response``, a
        parsed body, or the exception raised while talking to LinkedIn.
    :return: what to show the user, empty only when LinkedIn said nothing.
    :rtype: str
    """
    payload = _linkedin_error_payload(error)
    inputs = _linkedin_error_inputs(payload)
    if inputs:
        return "\n".join(inputs)
    for key in _ERROR_DETAIL_KEYS_LINKEDIN:
        detail = payload.get(key)
        if detail:
            return str(detail)
    body = getattr(error, "text", None)
    if body is None:
        body = str(error)
    return str(body).strip()


def _linkedin_error_code(error):
    """Return the code that names an error of LinkedIn, if it has one.

    Two keys are tried because the OAuth endpoint and the REST API name the
    error differently — ``error`` and ``serviceErrorCode`` — and the same
    failure can arrive through either.

    An error without a code answers the **empty string and never** ``None``:
    the callers compare the result against a tuple of known codes, and a
    ``None`` there would have to be guarded for on every one of them.

    :param error: a ``requests.Response``, a parsed body, or the exception
        raised while talking to LinkedIn.
    :return: the code LinkedIn gave the error, empty when it gave none.
    :rtype: str
    """
    payload = _linkedin_error_payload(error)
    for key in _ERROR_CODE_KEYS_LINKEDIN:
        code = payload.get(key)
        if code:
            return str(code)
    return ""


def _linkedin_is_credentials_error(error):
    """Return whether LinkedIn refused the authorization of the account.

    Those are the only errors worth retrying after renewing the token, so
    they are told apart from everything else LinkedIn may refuse. The HTTP
    status is checked too: an expired token is answered with a 401 that does
    not always carry one of the known codes.

    :param error: a ``requests.Response`` or the parsed answer of LinkedIn.
    :rtype: bool
    """
    if getattr(error, "status_code", None) == 401:
        return True
    return _linkedin_error_code(error) in _ERROR_CREDENTIALS_CODES_LINKEDIN


def epoch_milliseconds(value):
    """Read a moment as UTC and return it in milliseconds since the epoch.

    The LinkedIn APIs take their time windows in epoch milliseconds, so this
    is the conversion every call that carries a range needs. How wide a
    window is or how far back it reaches is a decision of each endpoint and
    stays with its caller.

    Values are read the way the ORM writes them: a ``datetime`` field is
    stored naive in UTC and ``fields.Datetime.now()`` answers the same way,
    so a naive value is stamped as UTC before converting. Without that stamp
    ``datetime.timestamp()`` would read it as local time of the process and
    the window asked for would shift with the server's ``TZ``.

    A string, a ``date`` and a ``datetime`` all name a moment here, because
    the callers get their bounds from a field, from a default or from a
    literal, and none of them should have to convert first. A tz-aware
    ``datetime`` is rejected by ``fields.Datetime.to_datetime`` with
    ``ValueError``; that is deliberate, tolerating it would hide the mistake
    instead of pointing at it.

    :param value: str | date | datetime -- the moment to convert, understood
        as UTC.
    :return: the same instant in milliseconds since the epoch.
    :rtype: int
    :raises ValueError: if ``value`` is a tz-aware ``datetime``.
    """
    value = fields.Datetime.to_datetime(value)
    return int(value.replace(tzinfo=timezone.utc).timestamp() * 1000)
