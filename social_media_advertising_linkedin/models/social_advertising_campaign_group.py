# Copyright 2026 Binhex <https://www.binhex.cloud>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

from ..social_advertising_linkedin_utils import (
    _ENDPOINT_AD_CAMPAIGN_GROUPS_LINKEDIN,
    run_schedule_window_linkedin,
)
from .social_advertising_campaign import LINKEDIN_LOCKED_CODES, LINKEDIN_START_MARGIN


class SocialAdvertisingCampaignGroup(models.Model):
    """Synchronization of the group with a LinkedIn Ads campaign group."""

    _inherit = "social.advertising.campaign.group"

    media_type = fields.Selection(related="media_id.media_type")
    currency_id = fields.Many2one(
        "res.currency",
        help="Currency of the total budget, sent to LinkedIn as the currency "
        "code of the campaign group. LinkedIn only accepts the currency of "
        "its advertising account.",
    )
    total_budget = fields.Monetary(
        tracking=True,
        help="Maximum amount to spend across all the campaigns and "
        "creatives of this group for its entire duration. It cannot be "
        "lower than the daily budgets of its campaigns.",
    )
    linkedin_needs_update = fields.Boolean(
        string="LinkedIn Pending Changes",
        readonly=True,
        copy=False,
        help="The campaign group was modified in Odoo after being "
        "synchronized with LinkedIn. Use the 'Update in LinkedIn' button "
        "to push the local values.",
    )
    linkedin_locked = fields.Boolean(
        compute="_compute_linkedin_locked",
        store=True,
        help="LinkedIn no longer accepts changes on this record.",
    )

    @api.depends("stage_id", "stage_id.code", "media_id", "media_id.media_type")
    def _compute_linkedin_locked(self):
        for group in self:
            group.linkedin_locked = (
                group.media_id.media_type == "linkedin"
                and group.stage_id.code in LINKEDIN_LOCKED_CODES
            )

    def _linkedin_sync_fields(self):
        """Fields pushed to LinkedIn, flagged as pending when changed here."""
        return ("name", "total_budget", "currency_id")

    def write(self, vals):
        sync_change = not self.env.context.get("skip_linkedin_needs_update") and any(
            field in vals for field in self._linkedin_sync_fields()
        )
        if sync_change:
            locked = self.filtered("linkedin_locked")
            if locked:
                raise UserError(
                    _(
                        "The campaign group %(names)s cannot be modified "
                        "because of its LinkedIn status (%(status)s).",
                        names=", ".join(locked.mapped("display_name")),
                        status=", ".join(locked.mapped("stage_id.name")),
                    )
                )
        res = super().write(vals)
        if sync_change:
            to_flag = self.filtered(
                lambda g: g.remote_ref
                and g.media_type == "linkedin"
                and not g.linkedin_needs_update
            )
            if to_flag:
                super(SocialAdvertisingCampaignGroup, to_flag).write(
                    {"linkedin_needs_update": True}
                )
        return res

    @api.constrains("total_budget")
    def _check_total_budget(self):
        """Lowering the total budget must not leave the campaigns over it."""
        if self.env.context.get("skip_linkedin_budget_check"):
            return
        self._check_linkedin_total_budget()

    def _check_linkedin_total_budget(self):
        """Raise when the daily budgets of a group exceed its total budget.

        Shared by both sides of the rule: the campaign checks it when its
        daily budget or its group changes, the group when its total budget
        does.
        """
        for group in self:
            if not group.total_budget:
                continue
            daily_budgets = sum(group.campaign_ids.mapped("daily_budget"))
            if group.total_budget < daily_budgets:
                raise ValidationError(
                    _(
                        "The daily budgets of the campaigns of the group "
                        "%(group)s add up to %(daily_budgets)s, which exceeds "
                        "its total budget of %(total_budget)s.",
                        group=group.display_name,
                        daily_budgets=daily_budgets,
                        total_budget=group.total_budget,
                    )
                )

    def _get_linkedin_account(self):
        """Return the social account used to call the LinkedIn API.

        The account decides which advertising account the group is written
        to, so it is never guessed: it comes from the campaigns of the group,
        and the database is only used as a fallback when it holds exactly one
        LinkedIn account. Anything else is ambiguous and raises, because
        picking the wrong one would create, update or archive the group in the
        advertising account of another advertiser.

        :return: the account, possibly empty when none exists at all.
        :rtype: recordset
        :raises UserError: when several accounts could be used.
        """
        self.ensure_one()
        accounts = self.campaign_ids.account_ids.filtered(
            lambda account: account.media_id.media_type == "linkedin"
        )
        if not accounts:
            accounts = self.env["social.account"].search(
                [("media_id.media_type", "=", "linkedin")], order="id"
            )
            if len(accounts) > 1:
                raise UserError(
                    _(
                        "The campaign group %(group)s is not linked to any "
                        "LinkedIn account and the database holds several of "
                        "them. Set the account on one of its campaigns to "
                        "choose the advertising account to use.",
                        group=self.display_name,
                    )
                )
        elif len(accounts) > 1:
            raise UserError(
                _(
                    "The campaigns of the group %(group)s point to several "
                    "LinkedIn accounts (%(accounts)s). Leave a single one so "
                    "the advertising account to use is unambiguous.",
                    group=self.display_name,
                    accounts=", ".join(accounts.mapped("display_name")),
                )
            )
        return accounts

    def _linkedin_create_group(self, account, advertising_account_urn):
        """Create this campaign group on LinkedIn in DRAFT status.

        DRAFT keeps it from spending budget until it is activated on
        Campaign Manager.

        :param account: The social.account used to call the LinkedIn API.
        :param advertising_account_urn: The advertising account URN.
        :return: The campaign group LinkedIn URN.
        :rtype: str
        """
        self.ensure_one()
        stage = self.env["social.stage"]._require_linkedin_stage("group", "DRAFT")
        start, end = run_schedule_window_linkedin()
        response = account._request_linkedin(
            method="POST",
            endpoint=(
                _ENDPOINT_AD_CAMPAIGN_GROUPS_LINKEDIN
                % advertising_account_urn.split(":")[-1]
            ),
            headers=account.media_id._get_linkedin_headers(account.sudo().access_token),
            json_data={
                "account": advertising_account_urn,
                "name": self.name,
                "runSchedule": {
                    "start": start,
                    "end": end,
                },
                "status": "DRAFT",
                "totalBudget": {
                    "amount": f"{self.total_budget}",
                    "currencyCode": self.currency_id.name,
                },
            },
            return_json=False,
        )
        if response.status_code != 201:
            raise UserError(
                _(
                    "The campaign group could not be created on LinkedIn: %(error)s",
                    error=self.env["social.account"]._linkedin_error_message(response),
                )
            )
        urn = (
            "urn:li:sponsoredCampaignGroup:"
            f"{response.headers.get('Location').split('/')[-1]}"
        )
        self.with_context(skip_linkedin_needs_update=True).write(
            {
                "remote_ref": urn,
                "stage_id": stage.id,
                "advertising_account_id": account._get_advertising_account(
                    advertising_account_urn
                ).id,
            }
        )
        return urn

    def _linkedin_runschedule_values(self):
        """Return a fresh run schedule when LinkedIn would reject the stored one.

        LinkedIn validates the whole group on a partial update, and a group
        left in DRAFT keeps the start date given on creation, which is in
        the past as soon as some time goes by (``DATE_TOO_EARLY``). A group
        already running keeps its own dates, which LinkedIn accepts.

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

    def action_publish_linkedin(self):
        """Create the campaign group on LinkedIn in DRAFT status.

        The group is also created automatically when the first campaign of
        the group is published with the 'Create in LinkedIn' button.
        """
        self.ensure_one()
        if self.remote_ref:
            raise UserError(_("The campaign group already exists on LinkedIn."))
        errors = []
        if not self.currency_id:
            errors.append(_("The campaign group must have a currency."))
        if self.total_budget <= 0:
            errors.append(_("The campaign group total budget must be positive."))
        if errors:
            raise UserError("\n".join(errors))
        account = self._get_linkedin_account()
        if not account:
            raise UserError(
                _("No LinkedIn social account is available to create the group.")
            )
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
        self._linkedin_create_group(account, advertising_account_urn)
        self.message_post(body=_("Campaign group created on LinkedIn in draft status."))
        return True

    def action_update_linkedin(self):
        """Push the local name and total budget to LinkedIn."""
        self.ensure_one()
        if not self.remote_ref:
            raise UserError(_("The campaign group does not exist on LinkedIn yet."))
        if self.linkedin_locked:
            raise UserError(
                _(
                    "The campaign group cannot be updated because of its "
                    "LinkedIn status (%(status)s).",
                    status=self.stage_id.name,
                )
            )
        if not self.currency_id:
            raise UserError(_("The campaign group must have a currency."))
        account = self._get_linkedin_account()
        if not account:
            raise UserError(
                _("No LinkedIn social account is available to update the group.")
            )
        ad_account_id = account._require_linkedin_ad_account_id()
        response = account._request_linkedin(
            method="POST",
            endpoint=(
                f"{_ENDPOINT_AD_CAMPAIGN_GROUPS_LINKEDIN % ad_account_id}/"
                f"{self.remote_ref.split(':')[-1]}"
            ),
            headers=account.media_id._get_linkedin_headers(
                account.sudo().access_token,
                x_restli_method="PARTIAL_UPDATE",
            ),
            json_data={
                "patch": {
                    "$set": {
                        "name": f"{self.name}",
                        "totalBudget": {
                            "amount": f"{self.total_budget}",
                            "currencyCode": self.currency_id.name,
                        },
                        **self._linkedin_runschedule_values(),
                    }
                }
            },
            return_json=False,
        )
        if response.status_code in (200, 204):
            self.with_context(skip_linkedin_needs_update=True).write(
                {"linkedin_needs_update": False}
            )
            self.message_post(body=_("Campaign group updated on LinkedIn."))
        else:
            raise UserError(
                _(
                    "The campaign group could not be updated on LinkedIn: %(error)s",
                    error=self.env["social.account"]._linkedin_error_message(response),
                )
            )
        return True

    def action_archive_linkedin(self):
        """Archive the campaign group on LinkedIn.

        The Ads API does not allow deleting a group. LinkedIn applies the
        same status to its campaigns, so run an import afterwards.
        """
        self.ensure_one()
        if not self.remote_ref:
            raise UserError(_("The campaign group does not exist on LinkedIn yet."))
        if self.linkedin_locked:
            raise UserError(
                _(
                    "The campaign group cannot be archived because of its "
                    "LinkedIn status (%(status)s).",
                    status=self.stage_id.name,
                )
            )
        account = self._get_linkedin_account()
        if not account:
            raise UserError(
                _("No LinkedIn social account is available to archive the group.")
            )
        stage = self.env["social.stage"]._require_linkedin_stage("group", "ARCHIVED")
        ad_account_id = account._require_linkedin_ad_account_id()
        response = account._request_linkedin(
            method="POST",
            endpoint=(
                f"{_ENDPOINT_AD_CAMPAIGN_GROUPS_LINKEDIN % ad_account_id}/"
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
                    "The campaign group could not be archived on LinkedIn: %(error)s",
                    error=self.env["social.account"]._linkedin_error_message(response),
                )
            )
        self.with_context(skip_linkedin_needs_update=True).write(
            {"stage_id": stage.id, "linkedin_needs_update": False}
        )
        self.message_post(body=_("Campaign group archived on LinkedIn."))
        return True
