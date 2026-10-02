# Copyright 2026 Binhex <https://www.binhex.cloud>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from urllib.parse import quote

from odoo import fields
from odoo.tools import date_utils

from odoo.addons.social_media_linkedin.social_linkedin_utils import (
    epoch_milliseconds,
    linkedin_urn_id,
)

_URL_CAMPAIGN_MANAGER_LINKEDIN = "https://www.linkedin.com/campaignmanager/accounts/"


def campaign_manager_url_linkedin(ad_account_ref, section, parameter, remote_ref):
    """Return the Campaign Manager address of one entity.

    Campaign Manager has no page of its own per entity: every section is a
    list under the advertising account, and one entity is reached by
    filtering that list on its identifier, which travels the way the
    interface writes it, as a JSON array of a single element.

    :param ad_account_ref: URN or bare identifier of the advertising account.
    :param section: path of the section listing this kind of entity.
    :param parameter: query parameter that section filters on.
    :param remote_ref: URN or bare identifier of the entity.
    :rtype: str
    """
    identifier = linkedin_urn_id(remote_ref)
    return (
        f"{_URL_CAMPAIGN_MANAGER_LINKEDIN}{linkedin_urn_id(ad_account_ref)}/"
        f"{section}?{parameter}={quote(str([identifier]))}"
    )


_ENDPOINT_AD_ACCOUNTS_LINKEDIN = "/adAccounts"
_ENDPOINT_AD_ACCOUNT_USERS_LINKEDIN = "/adAccountUsers"
_ENDPOINT_AD_CAMPAIGN_GROUPS_LINKEDIN = "/adAccounts/%s/adCampaignGroups"
_ENDPOINT_AD_CAMPAIGNS_LINKEDIN = "/adAccounts/%s/adCampaigns"
_ENDPOINT_AD_ANALYTICS_LINKEDIN = "/adAnalytics"
_ENDPOINT_AD_CREATIVES_LINKEDIN = "/adAccounts/%s/creatives"

# The largest page the Ads API serves. It covers the two paging protocols
# the endpoints speak — the offset one (``count`` / ``start``) and the cursor
# one (``pageSize`` / ``pageToken``) — because the ceiling is the same for
# both and only the way to ask for the next page changes.
_PAGE_SIZE_LINKEDIN = 100
# The analytics finder takes the creatives it reports on in the query string,
# so asking for all of them at once ends up in a URL the API rejects.
_CHUNK_SIZE_ANALYTICS_LINKEDIN = 20
# What the analytics finder is asked to report. ``pivotValues`` is not a
# figure but the axis: it carries the URN of the creative or the campaign
# each row belongs to, and without it the figures come back with nothing to
# tie them to. The rest has to stay in step with the mapping that writes
# them onto the ad, since a field not asked for here simply arrives missing
# and is written as a zero.
_FIELDS_STATISTIC_LINKEDIN = (
    "actionClicks,adUnitClicks,clicks,costInUsd,"
    "externalWebsiteConversions,impressions,pivotValues"
)

_SCOPE_ADS_LINKEDIN = ["r_ads", "rw_ads", "r_ads_reporting"]

# How long the run schedule sent to LinkedIn lasts. A campaign and a campaign
# group are created with one, and the API validates the whole record on a
# partial update, so a schedule has to be sent again every time a DRAFT one
# is touched. Thirty days is what the Campaign Manager itself proposes, and
# it is a decision of LinkedIn: the base helpers only convert the bounds.
_RUN_SCHEDULE_DAYS_LINKEDIN = 30


def run_schedule_window_linkedin():
    """Return a fresh run schedule for LinkedIn, in epoch milliseconds.

    The window is always built at the moment of the call and never stored:
    LinkedIn refuses a schedule that starts in the past
    (``DATE_TOO_EARLY``), which is what a stored one becomes as soon as some
    time goes by.

    :return: the ``(start, end)`` pair of the window.
    :rtype: tuple(int, int)
    """
    start = fields.Datetime.now()
    end = date_utils.add(start, days=_RUN_SCHEDULE_DAYS_LINKEDIN)
    return epoch_milliseconds(start), epoch_milliseconds(end)


def default_statistics_window(start_date, end_date, months=1):
    """Complete the bounds of a statistics window that were left out.

    Every LinkedIn endpoint reporting figures takes a window, and the bounds
    do not always reach it: a cron has no dates to give, a form may have had
    only one of the two filled in, and a hook the framework calls without
    arguments has none at all. A missing bound is the ordinary case rather
    than a mistake, and filling it in one place keeps each of those callers
    from inventing a default of its own.

    The end defaults to now and not to the end of the day: LinkedIn has
    nothing to report about a moment that has not happened yet.

    The bounds are returned as they arrive, without being converted. What
    each endpoint expects — epoch milliseconds for the analytics finders, a
    ``(year:,month:,day:)`` struct for the Ads API — belongs to whoever
    builds the call.

    :param start_date: first moment asked for, ``months`` back when missing.
    :param end_date: last moment asked for, now when missing.
    :param months: how far back the default start reaches.
    :return: the ``(start, end)`` pair of the window.
    :rtype: tuple
    """
    start = start_date or fields.Datetime.subtract(fields.Datetime.now(), months=months)
    end = end_date or fields.Datetime.now()
    return start, end


def linkedin_date_struct(value):
    """Return one bound of an adAnalytics date range, as the API writes it.

    The finder takes its window as a Rest.li structure and not as a string,
    so every bound travels spelled out into its three numbers.

    :param value: the day to send, in any form ``fields.Date`` reads.
    :return: the ``(year:Y,month:M,day:D)`` literal of that day.
    :rtype: str
    """
    day = fields.Date.to_date(value)
    return f"(year:{day.year},month:{day.month},day:{day.day})"
