# Copyright 2025 Binhex <https://www.binhex.cloud>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models
from odoo.exceptions import UserError

from odoo.addons.social_media_base.social_utils import _generate_timestamps

from .utm_campaign import LINKEDIN_LOCKED_STATUSES


class UtmGroupCampaign(models.Model):
    """Synchronization of the group with a LinkedIn Ads campaign group."""

    _inherit = "utm.group.campaign"

    remote_ref = fields.Char(string="Linkedin URN")
    linkedin_status = fields.Selection(
        [
            ("draft", "Draft"),
            ("active", "Active"),
            ("paused", "Paused"),
            ("archived", "Archived"),
            ("canceled", "Canceled"),
            ("pending_deletion", "Pending deletion"),
            ("removed", "Removed"),
        ],
        string="LinkedIn Status",
        readonly=True,
        copy=False,
        help="Real status of the campaign group on LinkedIn. It is set when "
        "the group is created from Odoo and refreshed when campaigns are "
        "imported from LinkedIn.",
    )
    currency_id = fields.Many2one("res.currency")
    campaign_ids = fields.One2many("utm.campaign", "campaign_group_id")
    total_budget = fields.Float(
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

    def _linkedin_sync_fields(self):
        """Fields pushed to LinkedIn, flagged as pending when changed here."""
        return ("name", "total_budget")

    def write(self, vals):
        sync_change = not self.env.context.get("skip_linkedin_needs_update") and any(
            field in vals for field in self._linkedin_sync_fields()
        )
        if sync_change:
            locked = self.filtered(
                lambda g: g.linkedin_status in LINKEDIN_LOCKED_STATUSES
            )
            if locked:
                raise UserError(
                    self.env._(
                        "The campaign group %(names)s cannot be modified "
                        "because of its LinkedIn status (%(status)s).",
                        names=", ".join(locked.mapped("display_name")),
                        status=", ".join(locked.mapped("linkedin_status")),
                    )
                )
        res = super().write(vals)
        if sync_change:
            to_flag = self.filtered(
                lambda g: g.remote_ref and not g.linkedin_needs_update
            )
            if to_flag:
                super(UtmGroupCampaign, to_flag).write({"linkedin_needs_update": True})
        return res

    def _get_linkedin_account(self):
        """Return the social account used to call the LinkedIn API."""
        self.ensure_one()
        account = self.campaign_ids.account_id[:1]
        if not account:
            account = self.env["social.account"].search(
                [("media_id.media_type", "=", "linkedin")], limit=1
            )
        return account

    def _linkedin_create_group(self, account, advertising_account_id):
        """Create this campaign group on LinkedIn in DRAFT status.

        DRAFT keeps it from spending budget until it is activated on
        Campaign Manager.

        :param account: The social.account used to call the LinkedIn API.
        :param advertising_account_id: The advertising account URN.
        :return: The campaign group LinkedIn URN.
        :rtype: str
        """
        self.ensure_one()
        start, end = _generate_timestamps()
        response = account._request_linkedin(
            method="POST",
            endpoint="/adCampaignGroupsV2",
            headers=account.media_id._get_linkedin_headers(account.sudo().access_token),
            json_data={
                "account": advertising_account_id,
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
            token=True,
            return_json=False,
            linkedin_v2=True,
        )
        if response.status_code != 201:
            raise UserError(
                self.env._(
                    "Error creating group campaign in Linkedin: %(error)s",
                    error=self.env["social.account"]._linkedin_error_message(response),
                )
            )
        urn = (
            "urn:li:sponsoredCampaignGroup:"
            f"{response.headers.get('Location').split('/')[-1]}"
        )
        self.with_context(skip_linkedin_needs_update=True).write(
            {"remote_ref": urn, "linkedin_status": "draft"}
        )
        return urn

    def action_publish_linkedin(self):
        """Create the campaign group on LinkedIn in DRAFT status.

        The group is also created automatically when the first campaign of
        the group is published with the 'Create in LinkedIn' button.
        """
        self.ensure_one()
        if self.remote_ref:
            raise UserError(
                self.env._("The campaign group already exists on LinkedIn.")
            )
        errors = []
        if not self.currency_id:
            errors.append(self.env._("The campaign group must have a currency."))
        if self.total_budget <= 0:
            errors.append(
                self.env._("The campaign group total budget must be positive.")
            )
        if errors:
            raise UserError("\n".join(errors))
        account = self._get_linkedin_account()
        if not account:
            raise UserError(
                self.env._(
                    "No LinkedIn social account is available to create the group."
                )
            )
        advertising_account_id = account._get_linkedin_advertising_account()
        if not advertising_account_id:
            raise UserError(
                self.env._(
                    "No LinkedIn advertising account is available for the "
                    "account %(account)s.",
                    account=account.display_name,
                )
            )
        self._linkedin_create_group(account, advertising_account_id)
        self.message_post(
            body=self.env._("Campaign group created on LinkedIn in draft status.")
        )
        return True

    def action_update_linkedin(self):
        """Push the local name and total budget to LinkedIn."""
        self.ensure_one()
        if not self.remote_ref:
            raise UserError(
                self.env._("The campaign group does not exist on LinkedIn yet.")
            )
        if self.linkedin_status in LINKEDIN_LOCKED_STATUSES:
            raise UserError(
                self.env._(
                    "The campaign group cannot be updated because of its "
                    "LinkedIn status (%(status)s).",
                    status=self.linkedin_status,
                )
            )
        if not self.currency_id:
            raise UserError(self.env._("The campaign group must have a currency."))
        account = self._get_linkedin_account()
        if not account:
            raise UserError(
                self.env._(
                    "No LinkedIn social account is available to update the group."
                )
            )
        response = account._request_linkedin(
            method="POST",
            endpoint=f"/adCampaignGroupsV2/{self.remote_ref.split(':')[-1]}",
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
                    }
                }
            },
            token=True,
            return_json=False,
            linkedin_v2=True,
        )
        if response.status_code in (200, 204):
            self.with_context(skip_linkedin_needs_update=True).write(
                {"linkedin_needs_update": False}
            )
            self.message_post(body=self.env._("Campaign group updated on LinkedIn."))
        else:
            raise UserError(
                self.env._(
                    "Error updating campaign group in Linkedin: %(error)s",
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
            raise UserError(
                self.env._("The campaign group does not exist on LinkedIn yet.")
            )
        if self.linkedin_status in LINKEDIN_LOCKED_STATUSES:
            raise UserError(
                self.env._(
                    "The campaign group cannot be archived because of its "
                    "LinkedIn status (%(status)s).",
                    status=self.linkedin_status,
                )
            )
        account = self._get_linkedin_account()
        if not account:
            raise UserError(
                self.env._(
                    "No LinkedIn social account is available to archive the group."
                )
            )
        response = account._request_linkedin(
            method="POST",
            endpoint=f"/adCampaignGroupsV2/{self.remote_ref.split(':')[-1]}",
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
                self.env._(
                    "Error archiving campaign group in Linkedin: %(error)s",
                    error=self.env["social.account"]._linkedin_error_message(response),
                )
            )
        self.with_context(skip_linkedin_needs_update=True).write(
            {"linkedin_status": "archived", "linkedin_needs_update": False}
        )
        self.message_post(body=self.env._("Campaign group archived on LinkedIn."))
        return True
