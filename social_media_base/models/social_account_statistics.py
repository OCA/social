# Copyright 2026 Binhex <https://www.binhex.cloud>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


class SocialAccountStatistics(models.Model):
    """One row per account and day: what the social media reported for it."""

    _name = "social.account.statistics"
    _description = "Social Account Daily Statistics"
    _order = "date desc, account_id"
    _rec_name = "date"

    account_id = fields.Many2one(
        "social.account", required=True, ondelete="cascade", index=True
    )
    media_id = fields.Many2one(related="account_id.media_id", store=True, index=True)
    media_type = fields.Selection(related="account_id.media_id.media_type", store=True)
    user_id = fields.Many2one(related="account_id.user_id", store=True, index=True)
    company_id = fields.Many2one(
        related="account_id.company_id", store=True, index=True
    )
    date = fields.Date(required=True, index=True)

    click_count = fields.Integer(default=0)
    like_count = fields.Integer(default=0)
    comment_count = fields.Integer(default=0)
    share_count = fields.Integer(default=0)
    impression_count = fields.Integer(default=0)
    engagement = fields.Float(
        default=0,
        digits=(16, 4),
        group_operator="avg",
        help="Engagement rate as the social media reports it. It is a ratio, "
        "so periods are averaged instead of added up.",
    )

    _sql_constraints = [
        (
            "unique_account_date",
            "unique (account_id, date)",
            "There can only be one statistics row per account and day.",
        ),
    ]
