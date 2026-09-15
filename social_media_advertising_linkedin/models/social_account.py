# Copyright 2026 Binhex <https://www.binhex.cloud>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import logging

from odoo import Command, _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools import split_every

from odoo.addons.social_media_linkedin.social_linkedin_utils import (
    datetime_from_epoch_milliseconds,
    linkedin_urn_id,
)

from ..social_advertising_linkedin_utils import (
    _CHUNK_SIZE_ANALYTICS_LINKEDIN,
    _ENDPOINT_AD_ACCOUNT_USERS_LINKEDIN,
    _ENDPOINT_AD_ACCOUNTS_LINKEDIN,
    _ENDPOINT_AD_ANALYTICS_LINKEDIN,
    _ENDPOINT_AD_CAMPAIGN_GROUPS_LINKEDIN,
    _ENDPOINT_AD_CAMPAIGNS_LINKEDIN,
    _ENDPOINT_AD_CREATIVES_LINKEDIN,
    _FIELDS_STATISTIC_LINKEDIN,
    _PAGE_SIZE_LINKEDIN,
    _SCOPE_ADS_LINKEDIN,
    default_statistics_window,
    linkedin_date_struct,
)
from .social_advertising_campaign import LINKEDIN_DELETED_CODES

_logger = logging.getLogger(__name__)


class SocialAccount(models.Model):
    """LinkedIn Ads side of a social media account."""

    _inherit = "social.account"

    linkedin_missing_ads_scopes = fields.Char(
        compute="_compute_linkedin_missing_ads_scopes",
        help="The Advertising API scopes the token of this account was not "
        "granted. A token keeps the scopes it was issued with, so an account "
        "associated before this module was installed has to be authorized "
        "again to reach the Ads API.",
    )

    @api.depends("media_id", "linkedin_granted_scopes")
    def _compute_linkedin_missing_ads_scopes(self):
        """List the Advertising API scopes the token of the account lacks.

        Computed rather than checked when a button is pressed so the account
        says what is wrong before anything is called: LinkedIn is the one
        deciding what a token gets, and it answers a token without the ads
        scopes whenever the application has no Advertising API product.
        """
        for account in self:
            if account.media_id.media_type != "linkedin":
                account.linkedin_missing_ads_scopes = ""
                continue
            account.linkedin_missing_ads_scopes = ", ".join(
                account._missing_linkedin_scopes(_SCOPE_ADS_LINKEDIN)
            )

    def _advertising_media_types(self):
        return super()._advertising_media_types() + ["linkedin"]

    def _fetch_advertising_accounts(self):
        """Return every LinkedIn advertising account the member may reach."""
        res = super()._fetch_advertising_accounts()
        if self.media_id.media_type != "linkedin":
            return res
        self._check_linkedin_scopes(["r_ads"])
        account_urns = dict.fromkeys(self._fetch_linkedin_ad_account_urns())
        data_by_urn = {
            account_urn: self._fetch_linkedin_ad_account(account_urn)
            for account_urn in account_urns
        }
        currency_by_name = self._linkedin_currencies_by_name(data_by_urn.values())
        return res + [
            self._prepare_linkedin_advertising_account(
                account_urn, data, currency_by_name=currency_by_name
            )
            for account_urn, data in data_by_urn.items()
        ]

    def _linkedin_currencies_by_name(self, elements):
        """Return the currencies these ``adAccounts`` elements name, by name.

        Read once for the whole page: LinkedIn answers the currency as its
        code, and an advertising account per currency would be one query per
        advertising account.

        :param elements: The ``adAccounts`` elements of the page.
        :rtype: dict
        """
        names = {
            element.get("currency") for element in elements if element.get("currency")
        }
        return (
            self.env["res.currency"]
            .search([("name", "in", list(names))])
            .grouped("name")
        )

    def _prepare_linkedin_advertising_account(
        self, account_urn, data, currency_by_name=None
    ):
        """Map an ``adAccounts`` element to a ``social.advertising.account``.

        :param account_urn: The advertising account URN.
        :param data: The ``adAccounts`` element of that URN.
        :param currency_by_name: The currencies of the page by name, read by
            :meth:`~._linkedin_currencies_by_name`. Without it the currency
            of this element alone is read.
        :rtype: dict
        """
        Currency = self.env["res.currency"]
        currency = (
            currency_by_name.get(data.get("currency"), Currency)
            if currency_by_name is not None
            else Currency.search([("name", "=", data.get("currency"))], limit=1)
        )
        return {
            "remote_ref": account_urn,
            "name": data.get("name") or linkedin_urn_id(account_urn),
            "environment": "test" if data.get("test") else "production",
            "currency_id": currency.id,
            "linkedin_status": data.get("status") or False,
            "linkedin_type": data.get("type") or False,
            "linkedin_reference": data.get("reference") or "",
            "linkedin_serving_status": ", ".join(data.get("servingStatuses") or []),
        }

    def _get_linkedin_advertising_account(self):
        """Return the advertising account URN this account works with.

        Nothing is resolved on the fly: the advertising account is the one
        the user marked as in use. Campaigns, campaign groups and ads all
        belong to a single advertising account on LinkedIn, so guessing one
        would silently work against the wrong advertiser.

        :return: The advertising account URN or False when none is in use.
        :rtype: str | bool
        """
        return self.advertising_account_urn

    def _fetch_linkedin_ad_account_urns(self):
        """Return the advertising accounts the authorized member can reach.

        The ``search`` finder of ``adAccounts`` answers only to the partners
        of the Marketing API (``partnerApiAdAccounts``), so the accounts are
        discovered through the roles of the member instead, which every
        application with the Advertising API product may read.

        :return: The advertising account URNs.
        :rtype: list
        """
        urns = []
        start = 0
        while True:
            response = self._request_linkedin(
                endpoint=_ENDPOINT_AD_ACCOUNT_USERS_LINKEDIN,
                headers=self.media_id._get_linkedin_headers(self.sudo().access_token),
                params_fields=["q", "start", "count"],
                params_values={
                    "q": "authenticatedUser",
                    "start": start,
                    "count": _PAGE_SIZE_LINKEDIN,
                },
                return_json=False,
            )
            if response.status_code != 200:
                raise UserError(
                    _(
                        "The advertising accounts could not be read from LinkedIn: "
                        "%(error)s",
                        error=self._linkedin_error_message(response),
                    )
                )
            data = response.json()
            elements = data.get("elements", [])
            urns += [
                element["account"] for element in elements if element.get("account")
            ]
            start += _PAGE_SIZE_LINKEDIN
            if not elements or start >= data.get("paging", {}).get("total", 0):
                break
        return urns

    def _fetch_linkedin_ad_account(self, account_urn):
        """Return the advertising account of a URN.

        Its ``test`` flag is what tells the test accounts from the production
        ones, and the role of the member does not carry it.

        :rtype: dict
        """
        response = self._request_linkedin(
            endpoint=(
                f"{_ENDPOINT_AD_ACCOUNTS_LINKEDIN}/{linkedin_urn_id(account_urn)}"
            ),
            headers=self.media_id._get_linkedin_headers(self.sudo().access_token),
            return_json=False,
        )
        if response.status_code != 200:
            raise UserError(
                _(
                    "The advertising accounts could not be read from LinkedIn: "
                    "%(error)s",
                    error=self._linkedin_error_message(response),
                )
            )
        return response.json()

    def _get_linkedin_ad_account_id(self):
        """Return the identifier of the advertising account, without its URN.

        :return: The identifier or False when the account has no advertising
                 account.
        :rtype: str | bool
        """
        advertising_account = self._get_linkedin_advertising_account()
        return linkedin_urn_id(advertising_account) if advertising_account else False

    def _linkedin_no_advertising_account_message(self):
        """Return what to tell the user when no advertising account is in use.

        Nothing of the Ads API is addressed without one, so the same sentence
        is what the two helpers below raise and what the checks that only
        report the problem put on their list.

        :rtype: str
        """
        return _(
            "No LinkedIn advertising account is in use for the "
            "account %(account)s. Open its Advertising tab, "
            "fetch the advertising accounts and choose one.",
            account=self.display_name,
        )

    def _require_linkedin_advertising_account(self):
        """Return the advertising account URN in use, or raise.

        :rtype: str
        """
        advertising_account_urn = self._get_linkedin_advertising_account()
        if not advertising_account_urn:
            raise UserError(self._linkedin_no_advertising_account_message())
        return advertising_account_urn

    def _require_linkedin_ad_account_id(self):
        """Return the identifier of the advertising account, or raise.

        Every campaign and campaign group endpoint is scoped by advertising
        account, so an account without one cannot write anything on LinkedIn.

        :rtype: str
        """
        ad_account_id = self._get_linkedin_ad_account_id()
        if not ad_account_id:
            raise UserError(self._linkedin_no_advertising_account_message())
        return ad_account_id

    def _patch_linkedin(self, endpoint, values, content_type=None):
        """Send a partial update to the Ads API.

        Every write of this module is the same call: a ``POST`` carrying the
        ``PARTIAL_UPDATE`` Rest.li method and a ``$set`` patch. What the
        answer means is the caller's to decide, so it comes back unchecked
        and each one keeps the error it words for its own entity.

        :param endpoint: the entity to patch, identifier included.
        :param values: the fields to set.
        :param content_type: the media type of the body, for the endpoint
            that asks for one.
        :return: the answer of LinkedIn.
        """
        self.ensure_one()
        return self._request_linkedin(
            method="POST",
            endpoint=endpoint,
            headers=self.media_id._get_linkedin_headers(
                self.sudo().access_token,
                content_type=content_type,
                x_restli_method="PARTIAL_UPDATE",
            ),
            json_data={"patch": {"$set": values}},
            return_json=False,
        )

    def _fetch_linkedin_creatives(self, campaign_urns=None):
        """Fetch the creatives of the advertising account.

        The Creatives API replaces ``adCreativesV2``: it answers the status
        set by the advertiser and accepts both share and ugcPost references,
        and it paginates with a cursor instead of an index.

        :param campaign_urns: Restrict the search to these campaign URNs.
        :return: The creative elements, filtered by the environment of the
                 account.
        :rtype: list
        """
        ad_account_id = self._get_linkedin_ad_account_id()
        if not ad_account_id:
            return []
        params_fields = ["q", "sortOrder", "pageSize"]
        params_values = {
            "q": "criteria",
            "sortOrder": "ASCENDING",
            "pageSize": _PAGE_SIZE_LINKEDIN,
        }
        if campaign_urns:
            params_fields.append("campaigns")
            params_values["campaigns"] = list(campaign_urns)
        elements = self._paginate_linkedin_ads(
            _ENDPOINT_AD_CREATIVES_LINKEDIN % ad_account_id,
            params_fields,
            params_values,
            _("The ads could not be read from LinkedIn: %(error)s"),
        )
        # The creatives are filtered by the environment of the account: a
        # production account must never see the test entities of the
        # application.
        is_test = self.environment == "test"
        return [
            element
            for element in elements
            if bool(element.get("isTest", False)) == is_test
        ]

    def _paginate_linkedin_ads(
        self, endpoint, params_fields, params_values, error_message
    ):
        """Read every page of an Ads finder, following its cursor.

        The finders of the Ads API paginate with a cursor since the version
        202401: the answer carries the token of the next page in its
        metadata, and the run stops on the page that brings no token or no
        element.

        :param endpoint: the Ads API endpoint to read.
        :param params_fields: the query parameters, ``pageToken`` aside.
        :param params_values: their values, ``pageToken`` aside.
        :param error_message: the already translated message to raise when
            LinkedIn refuses, carrying a ``%(error)s`` for the detail. Each
            caller words its own: what could not be read is what the user
            needs to be told.
        :return: every element of every page, in the order they came.
        :rtype: list
        """
        elements = []
        page_token = None
        while True:
            page_fields = params_fields
            page_values = params_values
            if page_token:
                page_fields = params_fields + ["pageToken"]
                page_values = {**params_values, "pageToken": page_token}
            response = self._request_linkedin(
                endpoint=endpoint,
                headers=self.media_id._get_linkedin_headers(self.sudo().access_token),
                params_fields=page_fields,
                params_values=page_values,
                return_json=False,
            )
            if response.status_code != 200:
                raise UserError(
                    error_message % {"error": self._linkedin_error_message(response)}
                )
            data = response.json()
            page_elements = data.get("elements", [])
            elements += page_elements
            page_token = data.get("metadata", {}).get("nextPageToken")
            if not page_elements or not page_token:
                break
        return elements

    def _fetch_linkedin_ad_entities(self, endpoint, search=None, fields=None):
        """Fetch every element of an Ads search finder, following pagination.

        The search finders paginate with a cursor since the version 202401:
        the answer carries the token of the next page in its metadata.

        :param endpoint: The Ads API endpoint (e.g. the campaigns of an
                         advertising account).
        :param search: The Rest.li search criteria, without the ``search=``
                       prefix (e.g. ``"(test:false)"``).
        :param fields: The fields to project, comma separated.
        :return: The list of elements.
        :rtype: list
        """
        params_fields = ["q", "pageSize"]
        params_values = {"q": "search", "pageSize": _PAGE_SIZE_LINKEDIN}
        if search:
            params_fields.append("search")
            params_values["search"] = search
        if fields:
            params_fields.append("fields")
            params_values["fields"] = fields
        return self._paginate_linkedin_ads(
            endpoint,
            params_fields,
            params_values,
            _("The campaigns could not be read from LinkedIn: %(error)s"),
        )

    def _prefetch_linkedin_upsert(
        self, groups, campaigns, SocialGroup, SocialAdvertisingCampaign, Currency
    ):
        """Read what the upsert loops resolve by remote reference.

        An import brings hundreds of elements, so everything they look up is
        read once for the whole batch instead of once per element.

        :return: The campaign groups and campaigns by URN, and the currencies
            by ISO code.
        :rtype: tuple
        """
        group_urns = [
            f"urn:li:sponsoredCampaignGroup:{element['id']}" for element in groups
        ]
        group_urns.extend(
            element["campaignGroup"]
            for element in campaigns
            if element.get("campaignGroup")
        )
        campaign_urns = [
            f"urn:li:sponsoredCampaign:{element['id']}" for element in campaigns
        ]
        currency_codes = [
            element.get("totalBudget", {}).get("currencyCode")
            for element in groups
            if element.get("totalBudget", {}).get("currencyCode")
        ]
        # Every index answers a recordset, and the loops that read them keep
        # the first record: the reference is unique per social media, which
        # these domains do not narrow.
        return (
            SocialGroup.search([("remote_ref", "in", group_urns)]).grouped(
                "remote_ref"
            ),
            SocialAdvertisingCampaign.search(
                [("remote_ref", "in", campaign_urns)]
            ).grouped("remote_ref"),
            Currency.search([("name", "in", currency_codes)]).grouped("name"),
        )

    def _upsert_linkedin_campaign_groups(
        self,
        groups,
        SocialGroup,
        group_by_urn,
        currency_by_name,
        stage_by_scope,
        advertising_account,
    ):
        """Create or update the campaign groups of an import batch.

        :param groups: adCampaignGroups elements.
        :return: The campaign groups by URN and the number of created ones.
        :rtype: tuple
        """
        groups_by_urn = {}
        new_groups = []
        new_group_urns = []
        for element in groups:
            urn = f"urn:li:sponsoredCampaignGroup:{element['id']}"
            total_budget = element.get("totalBudget", {})
            status = element.get("status") or ""
            vals = {
                "name": element.get("name", ""),
                "remote_ref": urn,
                "total_budget": float(total_budget.get("amount", 0) or 0),
                "media_id": self.media_id.id,
                "stage_id": stage_by_scope.get(("group", status), False),
                "advertising_account_id": advertising_account.id,
            }
            currency = currency_by_name.get(
                total_budget.get("currencyCode"), self.env["res.currency"]
            )[:1]
            if currency:
                vals["currency_id"] = currency.id
            group = group_by_urn.get(urn, SocialGroup)[:1]
            if not group:
                new_groups.append(vals)
                new_group_urns.append(urn)
                continue
            if group.linkedin_needs_update:
                group.message_post(
                    body=_(
                        "Import kept the local pending changes. "
                        "LinkedIn values: name: %(name)s, "
                        "total budget: %(total_budget)s %(currency)s",
                        name=vals["name"],
                        total_budget=vals["total_budget"],
                        currency=total_budget.get("currencyCode", ""),
                    )
                )
                for field in ("name", "total_budget", "currency_id"):
                    vals.pop(field, None)
            was_deleted = group.stage_id.code in LINKEDIN_DELETED_CODES
            group.with_context(skip_linkedin_needs_update=True).write(vals)
            if not was_deleted and group.stage_id.code in LINKEDIN_DELETED_CODES:
                group.message_post(
                    body=_(
                        "This campaign group was deleted on LinkedIn. It "
                        "is kept in Odoo as history because LinkedIn "
                        "still returns it with its performance data."
                    )
                )
            groups_by_urn[urn] = group
        if new_groups:
            created_groups = SocialGroup.create(new_groups)
            for index, new_urn in enumerate(new_group_urns):
                groups_by_urn[new_urn] = created_groups[index]
        return groups_by_urn, len(new_groups)

    def _upsert_linkedin_campaigns(self, groups, campaigns):
        """Create or update the campaign groups and campaigns from Ads elements.

        Records are searched and written with ``sudo()``: the record rule
        scopes campaigns by ``user_id``, so without it an importer would not
        see the records owned by other users and would create duplicates
        with the same URN.

        :param groups: adCampaignGroups elements.
        :param campaigns: adCampaigns elements.
        :return: The number of created groups and campaigns.
        :rtype: dict
        """
        SocialGroup = (
            self.env["social.advertising.campaign.group"]
            .sudo()
            .with_context(active_test=False, skip_linkedin_budget_check=True)
        )
        SocialAdvertisingCampaign = (
            self.env["social.advertising.campaign"]
            .sudo()
            .with_context(skip_linkedin_budget_check=True, active_test=False)
        )
        Currency = self.env["res.currency"]
        current_advertising_account = self.advertising_account_ids.filtered(
            "is_current"
        )[:1]
        advertising_account_by_urn = self.sudo().advertising_account_ids.grouped(
            "remote_ref"
        )
        counts = {"groups": 0, "campaigns": 0}
        groups_by_urn = {}
        stages = self.env["social.stage"].search(
            [("media_id.media_type", "=", "linkedin")]
        )
        stage_by_scope = {(stage.applies_to, stage.code): stage.id for stage in stages}
        campaign_fields = SocialAdvertisingCampaign._fields
        # Labels are resolved in the user language for the chatter messages.
        campaign_selections = {
            key: (
                field_name,
                dict(campaign_fields[field_name]._description_selection(self.env)),
            )
            for key, field_name in (
                ("format", "linkedin_format"),
                ("objectiveType", "linkedin_objective"),
                ("politicalIntent", "linkedin_political_intent"),
            )
        }
        (
            group_by_urn,
            campaign_by_urn,
            currency_by_name,
        ) = self._prefetch_linkedin_upsert(
            groups, campaigns, SocialGroup, SocialAdvertisingCampaign, Currency
        )
        groups_by_urn, counts["groups"] = self._upsert_linkedin_campaign_groups(
            groups,
            SocialGroup,
            group_by_urn,
            currency_by_name,
            stage_by_scope,
            current_advertising_account,
        )
        new_campaigns = []
        for element in campaigns:
            urn = f"urn:li:sponsoredCampaign:{element['id']}"
            group_urn = element.get("campaignGroup", "")
            group = (
                groups_by_urn.get(group_urn) or group_by_urn.get(group_urn, SocialGroup)
            )[:1]
            status = element.get("status") or ""
            vals = {
                "name": element.get("name", ""),
                "remote_ref": urn,
                "unit_cost": float(element.get("unitCost", {}).get("amount", 0) or 0),
                "daily_budget": float(
                    element.get("dailyBudget", {}).get("amount", 0) or 0
                ),
                "media_id": self.media_id.id,
                "account_ids": [Command.link(self.id)],
                "stage_id": stage_by_scope.get(("campaign", status), False),
                "linkedin_is_test": element.get("test", False),
                "advertising_account_id": advertising_account_by_urn.get(
                    element.get("account", ""), current_advertising_account
                ).id,
            }
            vals.update(
                {
                    field_name: element[key]
                    for key, (field_name, values) in campaign_selections.items()
                    if element.get(key) in values
                }
            )
            if group:
                vals["campaign_group_id"] = group.id
            campaign = campaign_by_urn.get(urn, SocialAdvertisingCampaign)[:1]
            if campaign:
                if campaign.name == vals["name"]:
                    vals.pop("name")
                if campaign.linkedin_needs_update:
                    political_intent = campaign_selections["politicalIntent"][1].get(
                        vals.get("linkedin_political_intent"), ""
                    )
                    campaign.message_post(
                        body=_(
                            "Import kept the local pending changes. "
                            "LinkedIn values: name: %(name)s, "
                            "unit cost: %(unit_cost)s, "
                            "daily budget: %(daily_budget)s, "
                            "campaign group: %(group)s, "
                            "political declaration: %(political_intent)s",
                            name=element.get("name", ""),
                            unit_cost=vals["unit_cost"],
                            daily_budget=vals["daily_budget"],
                            group=group.name if group else "",
                            political_intent=political_intent,
                        )
                    )
                    for field in (
                        "name",
                        "unit_cost",
                        "daily_budget",
                        "campaign_group_id",
                        "linkedin_political_intent",
                    ):
                        vals.pop(field, None)
                was_deleted = campaign.stage_id.code in LINKEDIN_DELETED_CODES
                campaign.with_context(skip_linkedin_needs_update=True).write(vals)
                if not was_deleted and campaign.stage_id.code in LINKEDIN_DELETED_CODES:
                    campaign.message_post(
                        body=_(
                            "This campaign was deleted on LinkedIn. It is "
                            "kept in Odoo as history because LinkedIn still "
                            "returns it with its performance data."
                        )
                    )
            else:
                new_campaigns.append(vals)
        if new_campaigns:
            SocialAdvertisingCampaign.create(new_campaigns)
            counts["campaigns"] += len(new_campaigns)
        return counts

    def _link_linkedin_creatives(self, creatives):
        """Link the creatives with the publications they promote.

        The creative is the only source relating a post with its campaign:
        the Posts API does not return it, so a publication imported from the
        wall gets its campaign here. Publications published from Odoo take it
        from their parent post instead and are never overwritten.

        :param creatives: Creatives API elements.
        :return: The number of newly linked posts.
        :rtype: int
        """
        PostAccount = self.env["social.post.account"].sudo()
        Campaign = self.env["social.advertising.campaign"].sudo()
        # ``grouped`` answers a recordset per key, and neither index is unique
        # by constraint: the publication has none on its remote reference, and
        # the campaign is unique per social media, which this domain does not
        # narrow. The first one wins, as it did.
        post_account_by_ref = PostAccount.search(
            [
                (
                    "remote_ref",
                    "in",
                    [
                        element.get("content", {}).get("reference")
                        for element in creatives
                        if element.get("content", {}).get("reference")
                    ],
                ),
                ("account_id", "=", self.id),
            ]
        ).grouped("remote_ref")
        campaigns_by_urn = Campaign.search(
            [
                (
                    "remote_ref",
                    "in",
                    [
                        element["campaign"]
                        for element in creatives
                        if element.get("campaign")
                    ],
                )
            ]
        ).grouped("remote_ref")
        linked = 0
        for element in creatives:
            reference = element.get("content", {}).get("reference")
            if not reference:
                continue
            post_account = post_account_by_ref.get(reference, PostAccount)[:1]
            if not post_account:
                continue
            values = {}
            creative_urn = str(element["id"])
            if post_account.creative_urn != creative_urn:
                values["creative_urn"] = creative_urn
            campaign = campaigns_by_urn.get(element.get("campaign"), Campaign)[:1]
            if (
                campaign
                and not post_account.post_id
                and post_account.social_campaign_id != campaign
            ):
                values["social_campaign_id"] = campaign.id
            if values:
                post_account.write(values)
                linked += 1
        return linked

    def action_import_campaigns(self):
        res = super().action_import_campaigns()
        if self.media_id.media_type != "linkedin":
            return res
        try:
            self._check_linkedin_scopes(["r_ads"])
            advertising_account_urn = self._get_linkedin_advertising_account()
            if not advertising_account_urn:
                return {
                    "success": False,
                    "message": self._linkedin_no_advertising_account_message(),
                    "groups": 0,
                    "campaigns": 0,
                    "ads": 0,
                }
            ad_account_id = linkedin_urn_id(advertising_account_urn)
            groups = self._fetch_linkedin_ad_entities(
                _ENDPOINT_AD_CAMPAIGN_GROUPS_LINKEDIN % ad_account_id
            )
            campaigns = self._fetch_linkedin_ad_entities(
                _ENDPOINT_AD_CAMPAIGNS_LINKEDIN % ad_account_id
            )
            campaign_urns = {
                f"urn:li:sponsoredCampaign:{element['id']}" for element in campaigns
            }
            creatives = self._fetch_linkedin_creatives(campaign_urns=campaign_urns)
        except UserError as error:
            return {
                "success": False,
                "message": str(error),
                "groups": 0,
                "campaigns": 0,
                "ads": 0,
            }
        counts = self._upsert_linkedin_campaigns(groups, campaigns)
        counts["ads"] = self._link_linkedin_creatives(creatives)
        return {
            "success": True,
            "message": _(
                "%(groups)s campaign group(s), %(campaigns)s campaign(s) "
                "and %(ads)s sponsored post(s) imported from LinkedIn.",
                **counts,
            ),
            "groups": counts["groups"],
            "campaigns": counts["campaigns"],
            "ads": counts["ads"],
        }

    def _get_linkedin_statistics(self, ads_ids=None, start_date=None, end_date=None):
        self._check_linkedin_scopes(["r_ads_reporting"])
        start_date, end_date = default_statistics_window(start_date, end_date)
        parse_start_date = linkedin_date_struct(start_date)
        parse_end_date = linkedin_date_struct(end_date)
        date_statistics_range = f"(start:{parse_start_date},end:{parse_end_date})"

        params_fields = [
            "q",
            "pivots",
            "timeGranularity",
            "dateRange",
            "fields",
        ]
        params_values = {
            "q": "statistics",
            "pivots": ["CAMPAIGN"],
            "timeGranularity": "ALL",
            "dateRange": date_statistics_range,
            "fields": _FIELDS_STATISTIC_LINKEDIN,
        }
        if ads_ids:
            params_fields.append("creatives")
            params_values.update(
                {
                    "pivots": ["CREATIVE"],
                    "creatives": list(ads_ids),
                }
            )
        response = self._request_linkedin(
            endpoint=_ENDPOINT_AD_ANALYTICS_LINKEDIN,
            headers=self.media_id._get_linkedin_headers(self.sudo().access_token),
            params_fields=params_fields,
            params_values=params_values,
            return_json=False,
        )

        if response.status_code == 200:
            statistics = response.json().get("elements", [])
        else:
            raise UserError(
                _(
                    "The statistics of the ads could not be read from LinkedIn: "
                    "%(error)s",
                    error=self._linkedin_error_message(response),
                )
            )
        return statistics

    def _get_linkedin_statistics_ads(self, ads_ids, start_date, end_date):
        """Return the statistics of the given ads over a date range.

        The creatives travel in the query string, so they are asked for in
        batches: a single call with every creative of an advertising account
        builds a URL the API refuses.

        :rtype: list
        """
        statistics = []
        for batch in split_every(_CHUNK_SIZE_ANALYTICS_LINKEDIN, ads_ids, list):
            statistics += self._get_linkedin_statistics(
                ads_ids=batch,
                start_date=start_date,
                end_date=end_date,
            )
        return statistics

    def _fetch_ad_refs(self):
        """Return the references of the creatives of the advertising account.

        Only the creatives are listed: their statistics, their campaigns and
        the posts they promote cost one call each and are not needed to tell
        whether the social media has something this database ignores.
        """
        res = super()._fetch_ad_refs()
        if self.media_id.media_type != "linkedin":
            return res
        return res | {
            str(element["id"])
            for element in self._fetch_linkedin_creatives()
            if element.get("id")
        }

    def _fetch_ads(self):
        """Return the creatives of the advertising account as ad values."""
        res = super()._fetch_ads()
        if self.media_id.media_type != "linkedin":
            return res
        start_date, end_date = default_statistics_window(None, None)
        return res + self._fetch_linkedin_ads(start_date, end_date)

    def _fetch_linkedin_ads(self, start_date, end_date):
        """Return the creatives of this account as ad values.

        The campaign and the promoted publication are resolved against what
        is already stored: the campaigns are imported by
        :meth:`action_import_campaigns` and the publications by the base
        module, so neither costs a call here. A creative promoting a post
        this database does not know keeps its statistics anyway, it simply
        has no publication linked.

        The dates bound the statistics window only. The Creatives API takes
        no date criteria, so the set of ads it answers is always the same.

        :param start_date: first day of the statistics window.
        :param end_date: last day of the statistics window.
        :rtype: list
        """
        res = []
        creatives = self._fetch_linkedin_creatives()
        if not creatives:
            return res
        statistic_by_ref = {}
        for statistic in self._get_linkedin_statistics_ads(
            [creative["id"] for creative in creatives],
            start_date=start_date,
            end_date=end_date,
        ):
            for pivot in statistic.get("pivotValues", []):
                statistic_by_ref[pivot] = statistic
        Campaign = self.env["social.advertising.campaign"].sudo()
        PostAccount = self.env["social.post.account"].sudo()
        Stage = self.env["social.stage"]
        # ``grouped`` answers a recordset per key, and the three indexes are
        # read as one record: the first one wins, as it did with the dicts.
        campaign_by_ref = Campaign.search(
            [
                (
                    "remote_ref",
                    "in",
                    [
                        creative["campaign"]
                        for creative in creatives
                        if creative.get("campaign")
                    ],
                ),
                ("media_id.media_type", "=", "linkedin"),
            ]
        ).grouped("remote_ref")
        post_account_by_ref = PostAccount.search(
            [
                (
                    "remote_ref",
                    "in",
                    [
                        creative.get("content", {}).get("reference")
                        for creative in creatives
                        if creative.get("content", {}).get("reference")
                    ],
                ),
                ("account_id", "=", self.id),
            ]
        ).grouped("remote_ref")
        stage_by_code = Stage.search(
            [
                ("media_id.media_type", "=", "linkedin"),
                ("applies_to", "=", "ad"),
            ]
        ).grouped("code")
        advertising_account = self.advertising_account_ids.filtered("is_current")[:1]
        # LinkedIn answers `costInUsd`, whatever the currency the advertising
        # account is billed in, so the cost is stored in dollars.
        currency = self.env.ref("base.USD", raise_if_not_found=False)
        for creative in creatives:
            remote_ref = str(creative["id"])
            statistic = statistic_by_ref.get(remote_ref, {})
            campaign = campaign_by_ref.get(creative.get("campaign"), Campaign)[:1]
            post_account = post_account_by_ref.get(
                creative.get("content", {}).get("reference"), PostAccount
            )[:1]
            stage = stage_by_code.get(creative.get("intendedStatus", ""), Stage)[:1]
            res.append(
                {
                    "remote_ref": remote_ref,
                    "advertising_account_id": advertising_account.id,
                    "campaign_id": campaign.id,
                    "post_account_id": post_account.id,
                    "stage_id": stage.id,
                    "status_detail": ", ".join(creative.get("servingHoldReasons", [])),
                    # The creation moment is stored in UTC, so every user
                    # reads it in his own time zone instead of the one of
                    # the process running the synchronization.
                    "created_date": datetime_from_epoch_milliseconds(
                        creative["createdAt"]
                    ),
                    "impression_count": statistic.get("impressions", 0),
                    "click_count": statistic.get("clicks", 0),
                    "action_click_count": statistic.get("actionClicks", 0),
                    "ad_unit_click_count": statistic.get("adUnitClicks", 0),
                    "conversion_count": statistic.get("externalWebsiteConversions", 0),
                    "cost": statistic.get("costInUsd", 0),
                    "currency_id": currency.id if currency else False,
                    "statistics_date_from": start_date,
                    "statistics_date_to": end_date,
                }
            )
        return res
