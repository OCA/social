# Copyright 2026 Binhex <https://www.binhex.cloud>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, fields, models

from odoo.addons.social_media_linkedin.social_linkedin_utils import (
    linkedin_urn_id,
)

from ..social_advertising_linkedin_utils import (
    _URL_CAMPAIGN_MANAGER_LINKEDIN,
)


class SocialAdvertisingAccount(models.Model):
    """LinkedIn side of an advertising account.

    Everything LinkedIn answers that the other advertising platforms do not
    have is declared here, so the generic model only holds what any of them
    reports.
    """

    _inherit = "social.advertising.account"

    linkedin_status = fields.Selection(
        [
            ("DRAFT", "Draft"),
            ("ACTIVE", "Active"),
            ("CANCELED", "Canceled"),
            ("PENDING_DELETION", "Pending deletion"),
            ("REMOVED", "Removed"),
        ],
        string="LinkedIn Status",
        readonly=True,
        help="Status of the advertising account on LinkedIn.",
    )
    linkedin_type = fields.Selection(
        [
            ("BUSINESS", "Business"),
            ("ENTERPRISE", "Enterprise"),
        ],
        string="LinkedIn Type",
        readonly=True,
        help="Enterprise advertising accounts are created by LinkedIn itself "
        "and cannot be test accounts.",
    )
    linkedin_serving_status = fields.Char(
        string="LinkedIn Serving Status",
        readonly=True,
        help="Why LinkedIn is serving the ads of this advertising account, "
        "or not: RUNNABLE when it is eligible, otherwise the reasons why it "
        "is not, such as BILLING_HOLD or ACCOUNT_TOTAL_BUDGET_HOLD.",
    )
    linkedin_reference = fields.Char(
        string="LinkedIn Owner",
        readonly=True,
        help="Organization or person the advertising account advertises on "
        "behalf of.",
    )

    def _get_display_reference(self):
        """Shorten the URN to the number LinkedIn shows in Campaign Manager.

        The whole ``urn:li:sponsoredAccount:123`` is what the API answers,
        but the advertiser only ever sees the identifier, which is also what
        the address of the account carries.

        :rtype: str
        """
        self.ensure_one()
        reference = super()._get_display_reference()
        if self.media_id.media_type != "linkedin":
            return reference
        return linkedin_urn_id(reference)

    @api.depends("media_id.media_type")
    def _compute_display_name(self):
        """Only declares the LinkedIn dependency of the computation."""
        return super()._compute_display_name()

    def _get_web_url(self):
        self.ensure_one()
        if self.media_id.media_type != "linkedin" or not self.remote_ref:
            return super()._get_web_url()
        identifier = linkedin_urn_id(self.remote_ref)
        return f"{_URL_CAMPAIGN_MANAGER_LINKEDIN}{identifier}/"
