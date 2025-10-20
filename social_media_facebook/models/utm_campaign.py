# Copyright 2025 Binhex <https://www.binhex.cloud>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class UtmCampaign(models.Model):
    _inherit = "utm.campaign"

    # Facebook Rollup Metrics (Feature #7.2)
    fb_impressions_total = fields.Integer(
        string="FB Impressions",
        compute="_compute_fb_rollup_metrics",
        store=False,
        help="Total impressions from Facebook posts/ads in this campaign",
    )
    fb_clicks_total = fields.Integer(
        string="FB Clicks",
        compute="_compute_fb_rollup_metrics",
        store=False,
        help="Total clicks from Facebook posts/ads in this campaign",
    )
    fb_spend_total = fields.Float(
        string="FB Spend",
        compute="_compute_fb_rollup_metrics",
        store=False,
        help="Total ad spend from Facebook ads in this campaign",
    )
    fb_leads_total = fields.Integer(
        string="FB Leads",
        compute="_compute_fb_rollup_metrics",
        store=False,
        help="Total leads from Facebook lead ads in this campaign",
    )
    fb_conversions_total = fields.Integer(
        string="FB Conversions",
        compute="_compute_fb_rollup_metrics",
        store=False,
        help="Total conversions from Facebook ads in this campaign",
    )
    fb_plays_total = fields.Integer(
        string="FB Video Plays",
        compute="_compute_fb_rollup_metrics",
        store=False,
        help="Total video plays from Facebook reels/videos in this campaign",
    )
    fb_engagement_total = fields.Integer(
        string="FB Engagement",
        compute="_compute_fb_rollup_metrics",
        store=False,
        help="Total engagement (likes + comments + shares) from Facebook content",
    )
    fb_reach_total = fields.Integer(
        string="FB Reach",
        compute="_compute_fb_rollup_metrics",
        store=False,
        help="Total reach from Facebook posts/ads in this campaign",
    )

    @api.depends("name")
    def _compute_fb_rollup_metrics(self):
        """
        Aggregate Facebook metrics from all posts associated with this campaign.
        Feature #7.2: Campaign rollups (impressions, clicks, spend, leads,
        conversions, plays) calculated from Facebook post accounts.
        """
        SocialPost = self.env["social.post"]

        for campaign in self:
            # Find all Facebook posts associated with this campaign
            fb_posts = SocialPost.search(
                [
                    ("campaign_id", "=", campaign.id),
                    ("media_id.media_type", "=", "facebook"),
                    ("fb_content_id", "!=", False),
                ]
            )

            # Aggregate metrics
            campaign.fb_impressions_total = sum(fb_posts.mapped("impressions"))
            campaign.fb_clicks_total = sum(fb_posts.mapped("clicks"))
            campaign.fb_spend_total = sum(fb_posts.mapped("spend"))
            campaign.fb_leads_total = sum(fb_posts.mapped("leads"))
            campaign.fb_conversions_total = sum(fb_posts.mapped("conversions"))
            campaign.fb_plays_total = sum(fb_posts.mapped("plays_total"))
            campaign.fb_engagement_total = sum(
                fb_posts.mapped("likes")
            ) + sum(fb_posts.mapped("comments")) + sum(fb_posts.mapped("shares"))
            campaign.fb_reach_total = sum(fb_posts.mapped("reach"))
