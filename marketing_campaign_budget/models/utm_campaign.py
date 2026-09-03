# Copyright 2026 Binhex Cloud
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import fields, models


class UtmCampaign(models.Model):
    _inherit = "utm.campaign"

    campaign_budget_amount = fields.Monetary(
        help="Planned budget for this campaign.",
        groups="sales_team.group_sale_salesman",
    )
    actual_cost = fields.Monetary(
        help="Real cost spent on this campaign.",
        groups="sales_team.group_sale_salesman",
    )

    _sql_constraints = [
        (
            "campaign_budget_amount_non_negative",
            "CHECK(campaign_budget_amount >= 0)",
            "The budget amount cannot be negative.",
        ),
        (
            "actual_cost_non_negative",
            "CHECK(actual_cost >= 0)",
            "The actual cost cannot be negative.",
        ),
    ]
