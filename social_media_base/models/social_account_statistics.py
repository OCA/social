# Copyright 2026 Binhex <https://www.binhex.cloud>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import json
from datetime import datetime, time, timedelta

from odoo import api, fields, models


class SocialAccountStatistics(models.Model):
    """One row per account and day: what the social media reported for it."""

    _name = "social.account.statistics"
    _description = "Daily Figures a Social Media Reports for an Account"
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
        aggregator="avg",
        help="Engagement rate as the social media reports it. It is a ratio, "
        "so periods are averaged instead of added up.",
    )
    engagement_percent = fields.Float(
        string="Engagement (%)",
        compute="_compute_engagement_percent",
        store=True,
        digits=(16, 2),
        help="Engagement rate shown as a percentage.",
    )

    @api.model
    def get_dashboard_data(self, period=30, account_id=False):
        """Aggregate the figures the statistics dashboard draws.

        One call builds everything the screen needs: the period series, the
        KPIs, the accounts to filter by and the posts with the most
        impressions. Nothing is stored for the screen itself: every figure
        comes from the daily rows and from the publications.
        """
        period = max(1, min(int(period or 30), 365))
        today = fields.Date.context_today(self)
        date_from = today - timedelta(days=period - 1)
        domain = [("date", ">=", date_from)]
        if account_id:
            account_id = int(account_id)
            domain.append(("account_id", "=", account_id))
        groups = self.formatted_read_group(
            domain,
            ["date:day"],
            [
                "impression_count:sum",
                "like_count:sum",
                "comment_count:sum",
                "share_count:sum",
                "click_count:sum",
                "engagement_percent:avg",
            ],
        )
        by_day = {}
        totals = {
            "impressions": 0,
            "likes": 0,
            "comments": 0,
            "shares": 0,
            "clicks": 0,
        }
        for group in groups:
            day = group.get("date:day")
            day_key = (
                day.strftime("%Y-%m-%d") if hasattr(day, "strftime") else str(day)[:10]
            )
            by_day[day_key] = {
                "impressions": group.get("impression_count:sum") or 0,
                "engagement": group.get("engagement_percent:avg") or 0,
            }
            totals["impressions"] += group.get("impression_count:sum") or 0
            totals["likes"] += group.get("like_count:sum") or 0
            totals["comments"] += group.get("comment_count:sum") or 0
            totals["shares"] += group.get("share_count:sum") or 0
            totals["clicks"] += group.get("click_count:sum") or 0
        series = []
        for offset in range(period):
            day = date_from + timedelta(days=offset)
            key = fields.Date.to_string(day)
            values = by_day.get(key, {})
            series.append(
                {
                    "date": key,
                    "impressions": values.get("impressions", 0),
                    "engagement": values.get("engagement", 0),
                }
            )
        interactions = (
            totals["likes"] + totals["comments"] + totals["shares"] + totals["clicks"]
        )
        engagement = (
            interactions * 100 / totals["impressions"] if totals["impressions"] else 0
        )
        accounts = self.env["social.account"].search_read(
            [],
            ["name", "media_type", "media_id", "follower_count"],
            limit=1000,
        )
        selected = [a for a in accounts if not account_id or a["id"] == account_id]
        followers = sum(a.get("follower_count") or 0 for a in selected)
        line_domain = [
            ("state", "=", "posted"),
            (
                "published_date",
                ">=",
                datetime.combine(date_from, time.min),
            ),
        ]
        if account_id:
            line_domain.append(("account_id", "=", account_id))
        top_posts = self.env["social.post.account"].search_read(
            line_domain,
            [
                "post_account_url",
                "message",
                "account_id",
                "published_date",
                "like_count",
                "comment_count",
                "impression_count",
                "image_urls",
                "media_type",
            ],
            order="impression_count desc",
            limit=5,
        )
        for post in top_posts:
            try:
                images = json.loads(post.get("image_urls") or "[]")
            except (TypeError, ValueError):
                images = []
            post["image_url"] = images[0] if images else False
        post_domain = [
            ("state", "in", ("published", "partially_published")),
            ("published_date", ">=", datetime.combine(date_from, time.min)),
        ]
        if account_id:
            post_domain.append(("account_ids", "in", [account_id]))
        posts_count = self.env["social.post"].search_count(post_domain)
        account_groups = self.formatted_read_group(
            domain,
            ["account_id"],
            [
                "impression_count:sum",
                "like_count:sum",
                "comment_count:sum",
                "share_count:sum",
                "click_count:sum",
                "engagement_percent:avg",
            ],
        )
        groups_by_account = {
            group["account_id"][0]: group
            for group in account_groups
            if group.get("account_id")
        }
        by_account = []
        for account in selected:
            group = groups_by_account.get(account["id"], {})
            impressions = group.get("impression_count:sum") or 0
            interactions = sum(
                group.get(f"{field}:sum") or 0
                for field in (
                    "like_count",
                    "comment_count",
                    "share_count",
                    "click_count",
                )
            )
            by_account.append(
                {
                    "id": account["id"],
                    "name": account["name"],
                    "media_type": account["media_type"],
                    "media_id": account["media_id"] and account["media_id"][0] or False,
                    "media_name": account["media_id"] and account["media_id"][1] or "",
                    "followers": account["follower_count"] or 0,
                    "impressions": impressions,
                    "interactions": interactions,
                    "engagement": (
                        interactions * 100 / impressions
                        if impressions
                        else group.get("engagement_percent:avg") or 0
                    ),
                }
            )
        by_account.sort(key=lambda row: row["impressions"], reverse=True)
        return {
            "period": period,
            "account_id": account_id or False,
            "accounts": accounts,
            "kpis": {
                "followers": followers,
                "impressions": totals["impressions"],
                "engagement": engagement,
                "posts": posts_count,
            },
            "series": series,
            "has_figures": bool(groups),
            "by_account": by_account,
            "top_posts": top_posts,
            "detailed_action_id": self.env.ref(
                "social_media_base.social_account_statistics_action"
            ).id,
        }

    @api.depends("engagement")
    def _compute_engagement_percent(self):
        for row in self:
            row.engagement_percent = (row.engagement or 0) * 100

    _unique_account_date = models.Constraint(
        "unique (account_id, date)",
        "There can only be one statistics row per account and day.",
    )
