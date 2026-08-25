# Copyright 2026 Binhex <https://www.binhex.cloud>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

from ..social_advertising_linkedin_utils import (
    _ENDPOINT_AD_CAMPAIGN_GROUPS_LINKEDIN,
    _ENDPOINT_AD_CAMPAIGNS_LINKEDIN,
    run_schedule_window_linkedin,
)

LINKEDIN_LOCKED_CODES = ("ARCHIVED", "CANCELED", "PENDING_DELETION", "REMOVED")
LINKEDIN_DELETED_CODES = ("PENDING_DELETION", "REMOVED")
LINKEDIN_START_MARGIN = 60


class SocialAdvertisingCampaign(models.Model):
    """Synchronization of the campaign with a LinkedIn Ads campaign."""

    _inherit = "social.advertising.campaign"

    linkedin_is_test = fields.Boolean(
        string="LinkedIn Test Campaign",
        readonly=True,
        copy=False,
        help="Whether LinkedIn flags this campaign as a test campaign.",
    )
    linkedin_format = fields.Selection(
        [
            ("STANDARD_UPDATE", "Standard update"),
            ("SINGLE_VIDEO", "Single video"),
        ],
        string="LinkedIn Ad Format",
        default="STANDARD_UPDATE",
        copy=False,
        tracking=True,
        help="Ad format of the campaign on LinkedIn. A campaign only accepts "
        "posts of its format, and LinkedIn does not allow changing it once "
        "the campaign is created, so a post with a video needs a campaign of "
        "the 'Single video' format.",
    )
    linkedin_objective = fields.Selection(
        [
            ("BRAND_AWARENESS", "Brand awareness"),
            ("VIDEO_VIEW", "Video views"),
            ("WEBSITE_VISIT", "Website visits"),
            ("ENGAGEMENT", "Engagement"),
        ],
        string="LinkedIn Objective",
        copy=False,
        tracking=True,
        help="Goal of the campaign on LinkedIn, required for the 'Single "
        "video' format:\n"
        "- Brand awareness: reach as many people as possible.\n"
        "- Video views: get the video of the post watched.\n"
        "- Website visits: send traffic to a page.\n"
        "- Engagement: get likes, comments and follows.\n"
        "LinkedIn has three more objectives (lead generation, website "
        "conversions and job applicants) that need a lead gen form, "
        "conversion tracking or LinkedIn Talent Solutions, which are "
        "configured outside Odoo and are therefore not offered here.",
    )
    linkedin_political_intent = fields.Selection(
        [
            ("NOT_POLITICAL", "Not political advertising"),
            ("POLITICAL", "Political advertising"),
            ("NOT_DECLARED", "Not declared"),
        ],
        string="LinkedIn Political Intent",
        default="NOT_POLITICAL",
        copy=False,
        tracking=True,
        help="Declaration required by LinkedIn to create a campaign: I "
        "confirm this is not political advertising. None of my ads qualify "
        "as political advertising under the law of the targeted countries, "
        "including EU law for ads targeted to the EU. Change it to "
        "'Political advertising' when the campaign does qualify as such.",
    )
    linkedin_needs_update = fields.Boolean(
        string="LinkedIn Pending Changes",
        readonly=True,
        copy=False,
        help="The campaign was modified in Odoo after being synchronized "
        "with LinkedIn. Use the 'Update in LinkedIn' button to push the "
        "local values.",
    )
    unit_cost = fields.Monetary(
        help="Bid amount per click, impression or other event depending on "
        "the pricing model. LinkedIn only applies it with manual, target "
        "cost or cost cap bidding; with automatic bidding it is ignored.",
        tracking=True,
    )
    daily_budget = fields.Monetary(
        help="Maximum amount to spend on this campaign per day. The "
        "campaign group total budget limits the overall spending.",
        tracking=True,
    )
    currency_id = fields.Many2one(
        "res.currency", related="campaign_group_id.currency_id"
    )
    linkedin_locked = fields.Boolean(
        compute="_compute_linkedin_locked",
        store=True,
        help="LinkedIn no longer accepts changes on this record.",
    )

    @api.depends("stage_id", "stage_id.code", "media_id", "media_id.media_type")
    def _compute_linkedin_locked(self):
        for campaign in self:
            campaign.linkedin_locked = (
                campaign.media_id.media_type == "linkedin"
                and campaign.stage_id.code in LINKEDIN_LOCKED_CODES
            )

    def _linkedin_account(self):
        """Return the LinkedIn account used to call the Ads API.

        LinkedIn uses a single advertising account per campaign, so of the
        ``account_ids`` of the base model only the first LinkedIn one is
        relevant; :meth:`_check_linkedin_single_account` guarantees there is
        at most one.

        :return: the account, empty when the campaign has none.
        :rtype: recordset
        """
        self.ensure_one()
        return self.account_ids.filtered(
            lambda account: account.media_id.media_type == "linkedin"
        )[:1]

    @api.constrains("account_ids", "media_id")
    def _check_linkedin_single_account(self):
        """Restrict LinkedIn campaigns to a single LinkedIn account.

        The restriction lives in the connector on purpose: the base module
        keeps ``account_ids`` open because another social media could allow
        several accounts per campaign.
        """
        for campaign in self:
            if campaign.media_id.media_type != "linkedin":
                continue
            linkedin_accounts = campaign.account_ids.filtered(
                lambda account: account.media_id.media_type == "linkedin"
            )
            if len(linkedin_accounts) > 1:
                raise ValidationError(
                    _("A LinkedIn campaign can only have one LinkedIn account.")
                )

    def _linkedin_runschedule_values(self):
        """Return a fresh run schedule when LinkedIn would reject the stored one.

        LinkedIn validates the whole campaign on a partial update, and a
        campaign left in DRAFT keeps the start date given on creation,
        which is in the past as soon as some time goes by
        (``DATE_TOO_EARLY``). Sending a new schedule is the only way to
        update or archive it. A campaign already running keeps its own
        dates, which LinkedIn accepts.

        :rtype: dict
        """
        self.ensure_one()
        if self.stage_id.code != "DRAFT":
            return {}
        start, end = run_schedule_window_linkedin()
        return {
            "runSchedule": {
                "start": start + LINKEDIN_START_MARGIN * 1000,
                "end": end,
            }
        }

    def _linkedin_sync_fields(self):
        """Fields pushed to LinkedIn, flagged as pending when changed here.

        ``media_id`` is guarded as well although it is not pushed: changing
        it is what decides whether the campaign is a LinkedIn one at all, so
        without it the lock of an archived campaign is escaped by taking it
        out of LinkedIn.
        """
        return (
            "name",
            "unit_cost",
            "daily_budget",
            "campaign_group_id",
            "linkedin_political_intent",
            "media_id",
        )

    def write(self, vals):
        sync_change = not self.env.context.get("skip_linkedin_needs_update") and any(
            field in vals for field in self._linkedin_sync_fields()
        )
        if sync_change:
            locked = self.filtered("linkedin_locked")
            if locked:
                raise UserError(
                    _(
                        "The campaign %(names)s cannot be modified because of "
                        "its LinkedIn status (%(status)s).",
                        names=", ".join(locked.mapped("display_name")),
                        status=", ".join(locked.mapped("stage_id.name")),
                    )
                )
        res = super().write(vals)
        if sync_change:
            to_flag = self.filtered(
                lambda c: c.remote_ref
                and c.media_type == "linkedin"
                and not c.linkedin_needs_update
            )
            if to_flag:
                super(SocialAdvertisingCampaign, to_flag).write(
                    {"linkedin_needs_update": True}
                )
        return res

    def _available_campaign(self):
        media_types = super()._available_campaign()
        media_types.append("linkedin")
        return media_types

    def _linkedin_publish_campaign_group(self, account, advertising_account_urn):
        """Ensure the campaign group of this campaign exists on LinkedIn.

        An existing URN is verified, a missing one is created in DRAFT so it
        does not spend budget until it is activated on Campaign Manager.

        :param account: The social.account used to call the LinkedIn API.
        :param advertising_account_urn: The advertising account URN.
        :return: The campaign group LinkedIn URN or False.
        :rtype: str | bool
        """
        self.ensure_one()
        if not self.campaign_group_id:
            raise UserError(
                _(
                    "The campaign %(campaign)s does not belong to a campaign " "group.",
                    campaign=self.display_name,
                )
            )
        group_campaign = False
        if advertising_account_urn:
            if self.campaign_group_id.remote_ref:
                ad_account_id = advertising_account_urn.split(":")[-1]
                group_campaign = account._request_linkedin(
                    endpoint=(
                        f"{_ENDPOINT_AD_CAMPAIGN_GROUPS_LINKEDIN % ad_account_id}/"
                        f"{self.campaign_group_id.remote_ref.split(':')[-1]}"
                    ),
                    headers=account.media_id._get_linkedin_headers(
                        account.sudo().access_token
                    ),
                    return_json=False,
                )
            if group_campaign and group_campaign.status_code == 200:
                return self.campaign_group_id.remote_ref
            elif not group_campaign or group_campaign.status_code == 404:
                group_campaign = self.campaign_group_id._linkedin_create_group(
                    account, advertising_account_urn
                )
            else:
                raise UserError(
                    _(
                        "The campaign group could not be checked on LinkedIn: "
                        "%(error)s",
                        error=self.env["social.account"]._linkedin_error_message(
                            group_campaign
                        ),
                    )
                )
        return group_campaign

    def _linkedin_verify_campaign(self, account):
        """Check that the stored campaign URN still exists on LinkedIn.

        :param account: The social.account used to call the LinkedIn API.
        :return: The campaign URN if it exists, False otherwise.
        :rtype: str | bool
        """
        self.ensure_one()
        if not self.remote_ref:
            return False
        ad_account_id = account._require_linkedin_ad_account_id()
        campaign = account._request_linkedin(
            endpoint=(
                f"{_ENDPOINT_AD_CAMPAIGNS_LINKEDIN % ad_account_id}/"
                f"{self.remote_ref.split(':')[-1]}"
            ),
            headers=account.media_id._get_linkedin_headers(account.sudo().access_token),
            return_json=False,
        )
        if campaign.status_code == 200:
            return self.remote_ref
        elif campaign.status_code == 404:
            return False
        raise UserError(
            _(
                "The campaign could not be checked on LinkedIn: %(error)s",
                error=self.env["social.account"]._linkedin_error_message(campaign),
            )
        )

    def _linkedin_create_campaign(
        self, account, advertising_account_urn, campaign_group_linkedin_urn
    ):
        """Create this campaign on LinkedIn under the given group.

        It is created in DRAFT so it does not spend budget until it is
        activated on Campaign Manager.

        :param account: The social.account used to call the LinkedIn API.
        :param advertising_account_urn: The advertising account URN.
        :param campaign_group_linkedin_urn: The campaign group URN.
        :return: The campaign LinkedIn URN or False.
        :rtype: str | bool
        """
        self.ensure_one()
        campaign = False
        if campaign_group_linkedin_urn:
            stage = self.env["social.stage"]._require_linkedin_stage(
                "campaign", "DRAFT"
            )
            start, end = run_schedule_window_linkedin()
            response = account._request_linkedin(
                method="POST",
                endpoint=(
                    _ENDPOINT_AD_CAMPAIGNS_LINKEDIN
                    % advertising_account_urn.split(":")[-1]
                ),
                headers=account.media_id._get_linkedin_headers(
                    account.sudo().access_token
                ),
                json_data={
                    "account": advertising_account_urn,
                    "campaignGroup": campaign_group_linkedin_urn,
                    "name": f"{self.name}",
                    "type": "SPONSORED_UPDATES",
                    "format": self.linkedin_format or "STANDARD_UPDATE",
                    **(
                        {"objectiveType": self.linkedin_objective}
                        if self.linkedin_objective
                        else {}
                    ),
                    "politicalIntent": self.linkedin_political_intent,
                    "offsiteDeliveryEnabled": False,
                    "runSchedule": {
                        "start": start,
                        "end": end,
                    },
                    "locale": {
                        "country": self.env.user.country_id.code or "US",
                        # A user whose language was deactivated has none, and
                        # LinkedIn fixes the locale when the campaign is
                        # created, so it never travels empty.
                        "language": (self.env.user.lang or "en_US").split("_")[0],
                    },
                    "unitCost": {
                        "amount": f"{self.unit_cost}",
                        "currencyCode": self.currency_id.name,
                    },
                    "dailyBudget": {
                        "amount": f"{self.daily_budget}",
                        "currencyCode": self.currency_id.name,
                    },
                    "status": "DRAFT",
                },
                return_json=False,
            )
            if response.status_code == 201:
                campaign = (
                    "urn:li:sponsoredCampaign:"
                    f"{response.headers.get('Location').split('/')[-1]}"
                )
                self.write(
                    {
                        "remote_ref": campaign,
                        "stage_id": stage.id,
                        "advertising_account_id": account._get_advertising_account(
                            advertising_account_urn
                        ).id,
                    }
                )
            else:
                raise UserError(
                    _(
                        "The campaign could not be created on LinkedIn: %(error)s",
                        error=self.env["social.account"]._linkedin_error_message(
                            response
                        ),
                    )
                )
        return campaign

    def _linkedin_publish_campaign(
        self, account, advertising_account_urn, campaign_group_linkedin_urn
    ):
        """Verify the stored campaign URN and create the campaign when missing.

        :param account: The social.account used to call the LinkedIn API.
        :param advertising_account_urn: The advertising account URN.
        :param campaign_group_linkedin_urn: The campaign group URN.
        :return: The campaign LinkedIn URN or False.
        :rtype: str | bool
        """
        self.ensure_one()
        campaign = self._linkedin_verify_campaign(account)
        if not campaign:
            campaign = self._linkedin_create_campaign(
                account, advertising_account_urn, campaign_group_linkedin_urn
            )
        return campaign

    def _validate_publish_linkedin(self):
        """Check that this campaign is ready to be created on LinkedIn."""
        self.ensure_one()
        errors = []
        if self.media_id.media_type != "linkedin":
            errors.append(_("The campaign media must be LinkedIn."))
        if not self.campaign_group_id:
            errors.append(_("The campaign must belong to a campaign group."))
        if not self._linkedin_account():
            errors.append(_("The campaign must have a social account."))
        if not self.currency_id:
            errors.append(_("The campaign group must have a currency."))
        if self.campaign_group_id and self.campaign_group_id.total_budget <= 0:
            errors.append(_("The campaign group total budget must be positive."))
        if self.unit_cost <= 0:
            errors.append(_("The campaign unit cost must be positive."))
        if self.daily_budget <= 0:
            errors.append(_("The campaign daily budget must be positive."))
        if self.linkedin_format == "SINGLE_VIDEO" and not self.linkedin_objective:
            errors.append(_("LinkedIn requires an objective for the video format."))
        if not self.linkedin_political_intent:
            errors.append(
                _(
                    "LinkedIn requires declaring whether the campaign is "
                    "political advertising."
                )
            )
        if errors:
            raise UserError("\n".join(errors))

    def action_publish_linkedin(self):
        """Create the campaign group and the campaign on LinkedIn in DRAFT.

        The campaign can then be selected on posts and activated from
        Campaign Manager when desired.
        """
        self.ensure_one()
        self._validate_publish_linkedin()
        account = self._linkedin_account()
        advertising_account_urn = account._get_linkedin_advertising_account()
        if not advertising_account_urn:
            raise UserError(
                _(
                    "No LinkedIn advertising account is in use for the "
                    "account %(account)s. Open its Advertising tab, "
                    "fetch the advertising accounts and choose one.",
                    account=account.display_name,
                )
            )
        group_urn = self._linkedin_publish_campaign_group(
            account, advertising_account_urn
        )
        try:
            self._linkedin_publish_campaign(account, advertising_account_urn, group_urn)
        except UserError as error:
            return self._register_publish_linkedin_failure(error)
        self.message_post(body=_("Campaign created on LinkedIn in draft status."))
        return True

    def _register_publish_linkedin_failure(self, error):
        """Report a campaign that could not be created on LinkedIn.

        :param error: The exception raised while creating the campaign.
        :return: A client action showing the error to the user.
        :rtype: dict
        """
        self.ensure_one()
        message = str(error)
        self.message_post(
            body=_(
                "The campaign could not be created on LinkedIn: %(error)s",
                error=message,
            )
        )
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Campaign not created on LinkedIn"),
                "message": message,
                "type": "danger",
                "sticky": True,
                "next": {"type": "ir.actions.act_window_close"},
            },
        }

    def action_update_linkedin(self):
        """Push the local name, unit cost and daily budget to LinkedIn."""
        self.ensure_one()
        if not self.remote_ref:
            raise UserError(_("The campaign does not exist on LinkedIn yet."))
        if self.linkedin_locked:
            raise UserError(
                _(
                    "The campaign cannot be updated because of its LinkedIn "
                    "status (%(status)s).",
                    status=self.stage_id.name,
                )
            )
        account = self._linkedin_account()
        if not account or not self.currency_id:
            raise UserError(
                _("The campaign must have a social account and a currency.")
            )
        if self.campaign_group_id and not self.campaign_group_id.remote_ref:
            raise UserError(
                _(
                    "The campaign group %(group)s does not exist on LinkedIn. "
                    "Create or import it before updating the campaign.",
                    group=self.campaign_group_id.display_name,
                )
            )
        values = {
            "name": f"{self.name}",
            "unitCost": {
                "amount": f"{self.unit_cost}",
                "currencyCode": self.currency_id.name,
            },
            "dailyBudget": {
                "amount": f"{self.daily_budget}",
                "currencyCode": self.currency_id.name,
            },
        }
        if self.campaign_group_id.remote_ref:
            values["campaignGroup"] = self.campaign_group_id.remote_ref
        if self.linkedin_political_intent:
            values["politicalIntent"] = self.linkedin_political_intent
        values.update(self._linkedin_runschedule_values())
        ad_account_id = account._require_linkedin_ad_account_id()
        response = account._request_linkedin(
            method="POST",
            endpoint=(
                f"{_ENDPOINT_AD_CAMPAIGNS_LINKEDIN % ad_account_id}/"
                f"{self.remote_ref.split(':')[-1]}"
            ),
            headers=account.media_id._get_linkedin_headers(
                account.sudo().access_token,
                x_restli_method="PARTIAL_UPDATE",
            ),
            json_data={"patch": {"$set": values}},
            return_json=False,
        )
        if response.status_code in (200, 204):
            self.with_context(skip_linkedin_needs_update=True).write(
                {"linkedin_needs_update": False}
            )
            self.message_post(body=_("Campaign updated on LinkedIn."))
        else:
            raise UserError(
                _(
                    "The campaign could not be updated on LinkedIn: %(error)s",
                    error=self.env["social.account"]._linkedin_error_message(response),
                )
            )
        return True

    def action_archive_linkedin(self):
        """Archive the campaign on LinkedIn.

        The Ads API does not allow deleting a campaign, so the campaign is
        kept in Odoo with its performance data and becomes read only.
        """
        self.ensure_one()
        if not self.remote_ref:
            raise UserError(_("The campaign does not exist on LinkedIn yet."))
        if self.linkedin_locked:
            raise UserError(
                _(
                    "The campaign cannot be archived because of its LinkedIn "
                    "status (%(status)s).",
                    status=self.stage_id.name,
                )
            )
        if self.campaign_group_id.stage_id.code == "DRAFT":
            raise UserError(
                _(
                    "LinkedIn does not archive a campaign whose campaign "
                    "group is still in draft status. Activate the group "
                    "%(group)s in Campaign Manager first, or archive the "
                    "group itself, which archives its campaigns.",
                    group=self.campaign_group_id.display_name,
                )
            )
        account = self._linkedin_account()
        if not account:
            raise UserError(_("The campaign must have a social account."))
        stage = self.env["social.stage"]._require_linkedin_stage("campaign", "ARCHIVED")
        ad_account_id = account._require_linkedin_ad_account_id()
        response = account._request_linkedin(
            method="POST",
            endpoint=(
                f"{_ENDPOINT_AD_CAMPAIGNS_LINKEDIN % ad_account_id}/"
                f"{self.remote_ref.split(':')[-1]}"
            ),
            headers=account.media_id._get_linkedin_headers(
                account.sudo().access_token,
                x_restli_method="PARTIAL_UPDATE",
            ),
            json_data={
                "patch": {
                    "$set": {
                        "status": "ARCHIVED",
                        **self._linkedin_runschedule_values(),
                    }
                }
            },
            return_json=False,
        )
        if response.status_code not in (200, 204):
            raise UserError(
                _(
                    "The campaign could not be archived on LinkedIn: %(error)s",
                    error=self.env["social.account"]._linkedin_error_message(response),
                )
            )
        self.with_context(skip_linkedin_needs_update=True).write(
            {"stage_id": stage.id, "linkedin_needs_update": False}
        )
        self.message_post(body=_("Campaign archived on LinkedIn."))
        return True

    @api.constrains("daily_budget", "campaign_group_id")
    def _check_daily_budget(self):
        """Keep the daily budgets of a group within its total budget.

        This is a rule of Odoo, not of LinkedIn: a group without total
        budget sets no limit there, and the import must never be stopped by
        it, since the values it brings are the ones LinkedIn already
        accepted.

        ``campaign_group_id`` is watched as well: moving a campaign into
        another group is one more way of going over its total budget.
        """
        if self.env.context.get("skip_linkedin_budget_check"):
            return
        self.campaign_group_id._check_linkedin_total_budget()
