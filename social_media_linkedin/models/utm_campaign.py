# Copyright 2025 Binhex <https://www.binhex.cloud>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

from odoo.addons.social_media_base.social_utils import _generate_timestamps

_logger = logging.getLogger(__name__)

LINKEDIN_LOCKED_STATUSES = ("archived", "canceled", "pending_deletion", "removed")
DELETED_LINKEDIN_STATUSES = ("pending_deletion", "removed")


class UtmCampaign(models.Model):
    """Synchronization of the campaign with a LinkedIn Ads campaign."""

    _inherit = "utm.campaign"

    remote_ref = fields.Char(string="Linkedin URN", copy=False)
    linkedin_status = fields.Selection(
        [
            ("draft", "Draft"),
            ("active", "Active"),
            ("paused", "Paused"),
            ("archived", "Archived"),
            ("completed", "Completed"),
            ("canceled", "Canceled"),
            ("pending_deletion", "Pending deletion"),
            ("removed", "Removed"),
        ],
        string="LinkedIn Status",
        readonly=True,
        copy=False,
        help="Real status of the campaign on LinkedIn. It is set when the "
        "campaign is created from Odoo and refreshed when campaigns are "
        "imported from LinkedIn.",
    )
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
        # The values are the ones of the ``adCampaignsV2`` endpoint used to
        # create the campaigns, which are singular. The versioned Campaigns
        # API documents them in plural and rejects these ones, so they must be
        # mapped if the creation ever moves to that endpoint.
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
    linkedin_needs_update = fields.Boolean(
        string="LinkedIn Pending Changes",
        readonly=True,
        copy=False,
        help="The campaign was modified in Odoo after being synchronized "
        "with LinkedIn. Use the 'Update in LinkedIn' button to push the "
        "local values.",
    )
    unit_cost = fields.Float(
        help="Bid amount per click, impression or other event depending on "
        "the pricing model. LinkedIn only applies it with manual, target "
        "cost or cost cap bidding; with automatic bidding it is ignored.",
        tracking=True,
    )
    daily_budget = fields.Float(
        help="Maximum amount to spend on this campaign per day. The "
        "campaign group total budget limits the overall spending.",
        tracking=True,
    )
    currency_id = fields.Many2one(
        "res.currency", related="campaign_group_id.currency_id"
    )
    media_type = fields.Selection(related="media_id.media_type")

    def _linkedin_sync_fields(self):
        """Fields pushed to LinkedIn, flagged as pending when changed here."""
        return ("name", "title", "unit_cost", "daily_budget", "campaign_group_id")

    def write(self, vals):
        sync_change = not self.env.context.get("skip_linkedin_needs_update") and any(
            field in vals for field in self._linkedin_sync_fields()
        )
        if sync_change:
            locked = self.filtered(
                lambda c: c.linkedin_status in LINKEDIN_LOCKED_STATUSES
            )
            if locked:
                raise UserError(
                    _(
                        "The campaign %(names)s cannot be modified because of "
                        "its LinkedIn status (%(status)s).",
                        names=", ".join(locked.mapped("display_name")),
                        status=", ".join(locked.mapped("linkedin_status")),
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
                super(UtmCampaign, to_flag).write({"linkedin_needs_update": True})
        return res

    def _available_campaign(self):
        media_type = super()._available_campaign()
        media_type.append("linkedin")
        return media_type

    def _linkedin_publish_campaign_group(self, account, advertising_account_id):
        """Ensure the campaign group of this campaign exists on LinkedIn.

        An existing URN is verified, a missing one is created in DRAFT so it
        does not spend budget until it is activated on Campaign Manager.

        :param account: The social.account used to call the LinkedIn API.
        :param advertising_account_id: The advertising account URN.
        :return: The campaign group LinkedIn URN or False.
        :rtype: str | bool
        """
        self.ensure_one()
        group_campaign = False
        if advertising_account_id:
            message_error = "Error creating group campaign in Linkedin:"
            if self.campaign_group_id.remote_ref:
                group_campaign = account._request_linkedin(
                    endpoint=(
                        "/adCampaignGroupsV2/"
                        f"{self.campaign_group_id.remote_ref.split(':')[-1]}"
                    ),
                    headers=account.media_id._get_linkedin_headers(
                        account.sudo().access_token
                    ),
                    token=True,
                    return_json=False,
                    linkedin_v2=True,
                )
            if group_campaign and group_campaign.status_code == 200:
                return self.campaign_group_id.remote_ref
            elif not group_campaign or group_campaign.status_code == 404:
                group_campaign = self.campaign_group_id._linkedin_create_group(
                    account, advertising_account_id
                )
            else:
                raise UserError(
                    _(
                        "%(message_error)s %(error_response)s",
                        message_error=message_error,
                        error_response=self.env[
                            "social.account"
                        ]._linkedin_error_message(group_campaign),
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
        campaign = account._request_linkedin(
            endpoint=f"/adCampaignsV2/{self.remote_ref.split(':')[-1]}",
            headers=account.media_id._get_linkedin_headers(account.sudo().access_token),
            return_json=False,
            linkedin_v2=True,
        )
        if campaign.status_code == 200:
            return self.remote_ref
        elif campaign.status_code == 404:
            return False
        raise UserError(
            _(
                "%(message_error)s %(error_response)s",
                message_error="Error creating campaign in Linkedin:",
                error_response=self.env["social.account"]._linkedin_error_message(
                    campaign
                ),
            )
        )

    def _linkedin_create_campaign(
        self, account, advertising_account_id, campaign_group_linkedin_urn
    ):
        """Create this campaign on LinkedIn under the given group.

        It is created in DRAFT so it does not spend budget until it is
        activated on Campaign Manager.

        :param account: The social.account used to call the LinkedIn API.
        :param advertising_account_id: The advertising account URN.
        :param campaign_group_linkedin_urn: The campaign group URN.
        :return: The campaign LinkedIn URN or False.
        :rtype: str | bool
        """
        self.ensure_one()
        campaign = False
        if campaign_group_linkedin_urn:
            message_error = "Error creating campaign in Linkedin:"
            start, end = _generate_timestamps()
            response = account._request_linkedin(
                method="POST",
                endpoint="/adCampaignsV2",
                headers=account.media_id._get_linkedin_headers(
                    account.sudo().access_token
                ),
                json_data={
                    "account": advertising_account_id,
                    "campaignGroup": campaign_group_linkedin_urn,
                    "name": f"{self.name}",
                    "type": "SPONSORED_UPDATES",
                    "format": self.linkedin_format or "STANDARD_UPDATE",
                    **(
                        {"objectiveType": self.linkedin_objective}
                        if self.linkedin_objective
                        else {}
                    ),
                    "offsiteDeliveryEnabled": False,
                    "runSchedule": {
                        "start": start,
                        "end": end,
                    },
                    "locale": {
                        "country": self.env.user.country_id.code or "US",
                        "language": self.env.user.lang.split("_")[0],
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
                token=True,
                return_json=False,
                linkedin_v2=True,
            )
            if response.status_code == 201:
                campaign = (
                    "urn:li:sponsoredCampaign:"
                    f"{response.headers.get('Location').split('/')[-1]}"
                )
                self.write({"remote_ref": campaign, "linkedin_status": "draft"})
            else:
                raise UserError(
                    _(
                        "%(message_error)s %(error_response)s",
                        message_error=message_error,
                        error_response=self.env[
                            "social.account"
                        ]._linkedin_error_message(response),
                    )
                )
        return campaign

    def _linkedin_publish_campaign(
        self, account, advertising_account_id, campaign_group_linkedin_urn
    ):
        """Verify the stored campaign URN and create the campaign when missing.

        :param account: The social.account used to call the LinkedIn API.
        :param advertising_account_id: The advertising account URN.
        :param campaign_group_linkedin_urn: The campaign group URN.
        :return: The campaign LinkedIn URN or False.
        :rtype: str | bool
        """
        self.ensure_one()
        campaign = self._linkedin_verify_campaign(account)
        if not campaign:
            campaign = self._linkedin_create_campaign(
                account, advertising_account_id, campaign_group_linkedin_urn
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
        if not self.account_id:
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
        if errors:
            raise UserError("\n".join(errors))

    def action_publish_linkedin(self):
        """Create the campaign group and the campaign on LinkedIn in DRAFT.

        The campaign can then be selected on posts and activated from
        Campaign Manager when desired.
        """
        self.ensure_one()
        self._validate_publish_linkedin()
        advertising_account_id = self.account_id._get_linkedin_advertising_account()
        if not advertising_account_id:
            raise UserError(
                _(
                    "No LinkedIn advertising account is available for the "
                    "account %(account)s.",
                    account=self.account_id.display_name,
                )
            )
        group_urn = self._linkedin_publish_campaign_group(
            self.account_id, advertising_account_id
        )
        self._linkedin_publish_campaign(
            self.account_id, advertising_account_id, group_urn
        )
        self.message_post(body=_("Campaign created on LinkedIn in draft status."))
        return True

    def action_update_linkedin(self):
        """Push the local name, unit cost and daily budget to LinkedIn."""
        self.ensure_one()
        if not self.remote_ref:
            raise UserError(_("The campaign does not exist on LinkedIn yet."))
        if self.linkedin_status in LINKEDIN_LOCKED_STATUSES:
            raise UserError(
                _(
                    "The campaign cannot be updated because of its LinkedIn "
                    "status (%(status)s).",
                    status=self.linkedin_status,
                )
            )
        if not self.account_id or not self.currency_id:
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
        account = self.account_id
        response = account._request_linkedin(
            method="POST",
            endpoint=f"/adCampaignsV2/{self.remote_ref.split(':')[-1]}",
            headers=account.media_id._get_linkedin_headers(
                account.sudo().access_token,
                x_restli_method="PARTIAL_UPDATE",
            ),
            json_data={"patch": {"$set": values}},
            token=True,
            return_json=False,
            linkedin_v2=True,
        )
        if response.status_code in (200, 204):
            self.with_context(skip_linkedin_needs_update=True).write(
                {"linkedin_needs_update": False}
            )
            self.message_post(body=_("Campaign updated on LinkedIn."))
        else:
            raise UserError(
                _(
                    "Error updating campaign in Linkedin: %(error)s",
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
        if self.linkedin_status in LINKEDIN_LOCKED_STATUSES:
            raise UserError(
                _(
                    "The campaign cannot be archived because of its LinkedIn "
                    "status (%(status)s).",
                    status=self.linkedin_status,
                )
            )
        account = self.account_id
        if not account:
            raise UserError(_("The campaign must have a social account."))
        response = account._request_linkedin(
            method="POST",
            endpoint=f"/adCampaignsV2/{self.remote_ref.split(':')[-1]}",
            headers=account.media_id._get_linkedin_headers(
                account.sudo().access_token,
                x_restli_method="PARTIAL_UPDATE",
            ),
            json_data={"patch": {"$set": {"status": "ARCHIVED"}}},
            token=True,
            return_json=False,
            linkedin_v2=True,
        )
        if response.status_code not in (200, 204):
            raise UserError(
                _(
                    "Error archiving campaign in Linkedin: %(error)s",
                    error=self.env["social.account"]._linkedin_error_message(response),
                )
            )
        self.with_context(skip_linkedin_needs_update=True).write(
            {"linkedin_status": "archived", "linkedin_needs_update": False}
        )
        self.message_post(body=_("Campaign archived on LinkedIn."))
        return True

    @api.constrains("daily_budget")
    def _check_daily_budget(self):
        for campaign in self:
            if campaign.campaign_group_id.total_budget < sum(
                campaign.campaign_group_id.campaign_ids.mapped("daily_budget")
            ):
                raise ValidationError(
                    _("The amount you want to add exceeds the campaign " "group limit.")
                )
