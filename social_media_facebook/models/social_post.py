# Copyright 2025 Binhex <https://www.binhex.cloud>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import json

from odoo import api, fields, models


class SocialPost(models.Model):
    _inherit = "social.post"

    # Facebook content type and ID
    fb_content_type = fields.Selection(
        [("post", "Post"), ("reel", "Reel"), ("ad", "Ad")],
        string="Facebook Content Type",
        help="Type of Facebook content",
    )
    fb_content_id = fields.Char(
        string="Facebook Content ID",
        index=True,
        help="Unique identifier for FB content (post/reel/ad)",
    )
    permalink_url = fields.Char(string="Permalink URL", help="Direct URL to the post")
    created_time = fields.Datetime(
        string="Created Time", help="When the post was created on Facebook"
    )
    last_sync_at = fields.Datetime(
        string="Last Synced At", help="Last time this post was synced from Facebook"
    )

    # Media
    media_url = fields.Char(string="Media URL", help="URL to media content")
    media_type = fields.Char(string="Media Type", help="Type of media (photo, video)")

    # Ads-only fields
    fb_ad_id = fields.Char(string="Facebook Ad ID", index=True, help="Facebook Ad ID")
    fb_adset_id = fields.Char(string="Facebook AdSet ID", help="Facebook AdSet ID")
    fb_campaign_id = fields.Char(
        string="Facebook Campaign ID", help="Facebook Campaign ID"
    )
    ad_name = fields.Char(string="Ad Name", help="Name of the ad")
    currency = fields.Char(string="Currency", default="USD", help="Currency code")

    # === POST METRICS (Organic) ===
    likes_count = fields.Integer(
        string="Likes", default=0, help="Total number of likes"
    )
    reactions_by_type_json = fields.Text(
        string="Reactions by Type",
        help="JSON breakdown of reactions (LIKE, LOVE, WOW, etc.)",
    )
    comments_count = fields.Integer(
        string="Comments", default=0, help="Number of comments"
    )
    shares_count = fields.Integer(string="Shares", default=0, help="Number of shares")
    impressions_total = fields.Integer(
        string="Impressions", default=0, help="Total impressions"
    )
    reach_unique = fields.Integer(
        string="Unique Reach", default=0, help="Unique people reached"
    )
    clicks_total = fields.Integer(string="Clicks", default=0, help="Total clicks")
    engagement_rate_pct = fields.Float(
        string="Engagement Rate %",
        compute="_compute_engagement_rate_pct",
        store=True,
        help="(likes + comments + shares + clicks) / impressions * 100",
    )

    # === AD METRICS (Paid) ===
    spend_amount = fields.Float(
        string="Spend Amount", default=0.0, digits=(16, 2), help="Total ad spend"
    )
    ctr_pct = fields.Float(
        string="CTR %", default=0.0, digits=(5, 2), help="Click-through rate %"
    )
    leads_total = fields.Integer(string="Leads", default=0, help="Total leads generated")
    conversions_total = fields.Integer(
        string="Conversions", default=0, help="Total conversions"
    )
    cpl_amount = fields.Float(
        string="Cost Per Lead",
        compute="_compute_cpl_amount",
        store=True,
        digits=(16, 2),
        help="Spend / Leads (zero-guard)",
    )

    # === REEL/VIDEO METRICS ===
    plays_total = fields.Integer(
        string="Total Plays", default=0, help="Total video views"
    )
    plays_unique = fields.Integer(
        string="Unique Plays", default=0, help="Unique video viewers"
    )
    watch_time_sec = fields.Integer(
        string="Watch Time (sec)", default=0, help="Total watch time in seconds"
    )
    completed_views = fields.Integer(
        string="Completed Views", default=0, help="Number of views that watched to completion"
    )
    completion_rate_pct = fields.Float(
        string="Completion Rate %",
        compute="_compute_completion_rate_pct",
        store=True,
        digits=(5, 2),
        help="Completion rate = completed views / total plays * 100",
    )
    avg_watch_time_sec = fields.Float(
        string="Avg Watch Time (sec)",
        compute="_compute_avg_watch_time_sec",
        store=True,
        digits=(10, 2),
        help="Average watch time per play",
    )
    saves_count = fields.Integer(
        string="Saves", default=0, help="Number of saves (if available)"
    )

    # === RAW SNAPSHOT ===
    metrics_json = fields.Text(
        string="Metrics Snapshot", help="Latest raw JSON snapshot from Facebook API"
    )
    metrics_updated_at = fields.Datetime(
        string="Metrics Updated At", help="When metrics_json was last updated"
    )

    # Origin indicator (computed field for easier filtering)
    is_synced_from_facebook = fields.Boolean(
        string="Synced from Facebook",
        compute="_compute_is_synced_from_facebook",
        store=True,
        help="True if this content was synced from Facebook, False if created in Odoo",
    )

    # === COMPUTED FIELDS ===

    @api.depends("fb_content_id")
    def _compute_is_synced_from_facebook(self):
        """Determine if content was synced from Facebook or created in Odoo"""
        for record in self:
            record.is_synced_from_facebook = bool(record.fb_content_id)

    @api.depends(
        "likes_count",
        "comments_count",
        "shares_count",
        "clicks_total",
        "impressions_total",
    )
    def _compute_engagement_rate_pct(self):
        """Compute engagement rate with zero-guard"""
        for record in self:
            if record.impressions_total > 0:
                numerator = (
                    record.likes_count
                    + record.comments_count
                    + record.shares_count
                    + record.clicks_total
                )
                record.engagement_rate_pct = (numerator / record.impressions_total) * 100
            else:
                record.engagement_rate_pct = 0.0

    @api.depends("spend_amount", "leads_total")
    def _compute_cpl_amount(self):
        """Compute cost per lead with zero-guard"""
        for record in self:
            if record.leads_total > 0:
                record.cpl_amount = record.spend_amount / record.leads_total
            else:
                record.cpl_amount = 0.0

    @api.depends("plays_total", "completed_views")
    def _compute_completion_rate_pct(self):
        """Compute video completion rate with zero-guard"""
        for record in self:
            if record.plays_total > 0:
                record.completion_rate_pct = (record.completed_views / record.plays_total) * 100
            else:
                record.completion_rate_pct = 0.0

    @api.depends("watch_time_sec", "plays_total")
    def _compute_avg_watch_time_sec(self):
        """Compute average watch time per play with zero-guard"""
        for record in self:
            if record.plays_total > 0:
                record.avg_watch_time_sec = record.watch_time_sec / record.plays_total
            else:
                record.avg_watch_time_sec = 0.0

    # === HELPER METHOD ===

    def write_metrics_snapshot(self, metrics_data):
        """Write metrics with timestamp and JSON snapshot"""
        self.ensure_one()
        from datetime import datetime

        values = dict(metrics_data)

        # Convert datetime objects to strings for JSON serialization
        json_data = {}
        for key, value in metrics_data.items():
            if isinstance(value, datetime):
                json_data[key] = value.isoformat() if value else None
            else:
                json_data[key] = value

        values.update(
            {
                "metrics_json": json.dumps(json_data, indent=2),
                "metrics_updated_at": fields.Datetime.now(),
                "last_sync_at": fields.Datetime.now(),
            }
        )
        self.write(values)

    # === SQL CONSTRAINTS ===

    _sql_constraints = [
        (
            "fb_content_unique",
            "unique(fb_content_id)",
            "This Facebook content has already been synced!",
        ),
    ]
