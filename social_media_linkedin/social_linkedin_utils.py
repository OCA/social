# Copyright 2025 Binhex <https://www.binhex.cloud>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

_URL_LINKEDIN = "https://www.linkedin.com/campaignmanager/accounts/"
_URL_REST_LINKEDIN = "https://api.linkedin.com/rest"
_URL_V2_LINKEDIN = "https://api.linkedin.com/v2"
_URL_AUTH_V2_LINKEDIN = "https://www.linkedin.com/oauth/v2"

_VERSION_STRING = "202502"

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

_FIELDS_CAMPAIGN_LINKEDIN = "id,name,test,account"
_FIELDS_STATISTIC_LINKEDIN = (
    "actionClicks,adUnitClicks,clicks,costInUsd,"
    "externalWebsiteConversions,impressions,pivotValues"
)
_URN_ORGANIZATION_LINKEDIN = "urn:li:organization:"
