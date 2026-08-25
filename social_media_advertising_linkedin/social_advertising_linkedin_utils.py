# Copyright 2026 Binhex <https://www.binhex.cloud>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields
from odoo.tools import date_utils

from odoo.addons.social_media_linkedin.social_linkedin_utils import (
    epoch_milliseconds,
)

_URL_CAMPAIGN_MANAGER_LINKEDIN = "https://www.linkedin.com/campaignmanager/accounts/"

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
