# Copyright 2025 Binhex <https://www.binhex.cloud>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import json

_URL_LINKEDIN = "https://www.linkedin.com/campaignmanager/accounts/"
_URL_FEED_UPDATE_LINKEDIN = "https://www.linkedin.com/feed/update/"
_URL_REST_LINKEDIN = "https://api.linkedin.com/rest"
_URL_V2_LINKEDIN = "https://api.linkedin.com/v2"
_URL_AUTH_V2_LINKEDIN = "https://www.linkedin.com/oauth/v2"

_VERSION_STRING = "202607"

_HEADERS_LINKEDIN = {
    "X-Restli-Protocol-Version": "2.0.0",
    "LinkedIn-Version": _VERSION_STRING,
}

_SCOPE_LINKEDIN = [
    "profile",
    "r_ads_reporting",
    "r_organization_social",
    "rw_organization_admin",
    "w_member_social",
    "r_ads",
    "w_organization_social",
    "rw_ads",
    "r_basicprofile",
    "r_organization_admin",
    "email",
    "r_1st_connections_size",
]

_FIELDS_CAMPAIGN_LINKEDIN = "id,name,test,account,format,objectiveType"
_FIELDS_STATISTIC_LINKEDIN = (
    "actionClicks,adUnitClicks,clicks,costInUsd,"
    "externalWebsiteConversions,impressions,pivotValues"
)
_URN_ORGANIZATION_LINKEDIN = "urn:li:organization:"
_URN_IMAGE_LINKEDIN = "urn:li:image:"
_URN_VIDEO_LINKEDIN = "urn:li:video:"

# The Videos API answers one upload instruction per part; every part but the
# last one has to hold exactly this many bytes.
_VIDEO_UPLOAD_PART_SIZE_LINKEDIN = 4 * 1024 * 1024

# A video is not publishable until LinkedIn finishes processing it, so its
# status is polled before creating the post. Both values can be overridden
# with the ``social_media_linkedin.video_poll_attempts`` and
# ``social_media_linkedin.video_poll_delay`` system parameters.
_VIDEO_POLL_ATTEMPTS_LINKEDIN = 30
_VIDEO_POLL_DELAY_LINKEDIN = 2

# Bootstrap context of the badge showing the ``status`` of a creative, which is
# the status set by the advertiser, as opposed to ``servingStatuses``, which
# explains why LinkedIn is serving it or not. Statuses that LinkedIn may add
# later fall back to the neutral context.
_ADS_STATUS_LEVELS_LINKEDIN = {
    "ACTIVE": "success",
    "DRAFT": "info",
    "PAUSED": "info",
    "ARCHIVED": "secondary",
    "CANCELED": "danger",
    "PENDING_DELETION": "danger",
}

# Keys holding the explanation of an error, in order of preference. The OAuth
# endpoints answer ``error_description``, the REST ones ``message``.
_ERROR_DETAIL_KEYS_LINKEDIN = ("error_description", "message")
# Keys holding the code that names the error.
_ERROR_CODE_KEYS_LINKEDIN = ("error", "serviceErrorCode")


def _linkedin_error_payload(error):
    """Return the answer of LinkedIn as a dict, when it is one.

    :param error: a ``requests.Response``, a parsed body, or anything that
        was raised while talking to LinkedIn.
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

    The answer of LinkedIn is never dropped: when it carries no known key,
    or when it is not JSON at all, its body is returned as it is.

    :rtype: str
    """
    payload = _linkedin_error_payload(error)
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

    :rtype: str
    """
    payload = _linkedin_error_payload(error)
    for key in _ERROR_CODE_KEYS_LINKEDIN:
        code = payload.get(key)
        if code:
            return str(code)
    return ""
