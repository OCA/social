# Copyright 2025 Kencove (https://www.kencove.com/)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import logging

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class SocialPost(models.Model):
    _inherit = "social.post"
    _order = "state asc, published_date desc"

    # Computed field for kanban/search views
    # (checks if ANY post_account is synced from FB)
    is_synced_from_facebook = fields.Boolean(
        string="Has Synced Facebook Content",
        compute="_compute_is_synced_from_facebook",
        search="_search_is_synced_from_facebook",
        help="True if any of the published accounts were synced from Facebook",
    )

    # === AGGREGATED FACEBOOK METRICS FOR CAMPAIGN ROLLUPS ===
    # These fields aggregate metrics from all Facebook post_accounts for this post
    # Used by utm.campaign to calculate campaign-level rollups (Feature #7.2)

    impressions = fields.Integer(
        string="Total Impressions",
        compute="_compute_facebook_aggregates",
        store=False,
        help="Total impressions from all Facebook accounts for this post",
    )
    clicks = fields.Integer(
        string="Total Clicks",
        compute="_compute_facebook_aggregates",
        store=False,
        help="Total clicks from all Facebook accounts for this post",
    )
    spend = fields.Float(
        string="Total Spend",
        compute="_compute_facebook_aggregates",
        store=False,
        help="Total ad spend from all Facebook accounts for this post",
    )
    leads = fields.Integer(
        string="Total Leads",
        compute="_compute_facebook_aggregates",
        store=False,
        help="Total leads from all Facebook accounts for this post",
    )
    conversions = fields.Integer(
        string="Total Conversions",
        compute="_compute_facebook_aggregates",
        store=False,
        help="Total conversions from all Facebook accounts for this post",
    )
    plays_total = fields.Integer(
        string="Total Video Plays",
        compute="_compute_facebook_aggregates",
        store=False,
        help="Total video plays from all Facebook accounts for this post",
    )
    likes = fields.Integer(
        string="Total Likes",
        compute="_compute_facebook_aggregates",
        store=False,
        help="Total likes from all Facebook accounts for this post",
    )
    comments = fields.Integer(
        string="Total Comments",
        compute="_compute_facebook_aggregates",
        store=False,
        help="Total comments from all Facebook accounts for this post",
    )
    shares = fields.Integer(
        string="Total Shares",
        compute="_compute_facebook_aggregates",
        store=False,
        help="Total shares from all Facebook accounts for this post",
    )
    reach = fields.Integer(
        string="Total Reach",
        compute="_compute_facebook_aggregates",
        store=False,
        help="Total reach from all Facebook accounts for this post",
    )
    fb_content_id = fields.Char(
        string="Facebook Content ID",
        compute="_compute_fb_content_id",
        store=False,
        help="Facebook content ID from the first Facebook post account (for filtering)",
    )

    @api.depends("post_account_ids.is_synced_from_facebook")
    def _compute_is_synced_from_facebook(self):
        """Check if ANY post_account for this post was synced from Facebook"""
        for record in self:
            record.is_synced_from_facebook = any(
                pa.is_synced_from_facebook for pa in record.post_account_ids
            )

    def _search_is_synced_from_facebook(self, operator, value):
        """Search for posts that have synced post_accounts"""
        # Find post_accounts that are synced from Facebook
        synced_accounts = self.env["social.post.account"].search_fetch(
            [("is_synced_from_facebook", "=", True)],
            ["post_id"],
        )
        post_ids = synced_accounts.mapped("post_id").ids

        if operator == "=" and value:
            return [("id", "in", post_ids)]
        elif operator == "=" and not value:
            return [("id", "not in", post_ids)]
        elif operator == "!=" and value:
            return [("id", "not in", post_ids)]
        elif operator == "!=" and not value:
            return [("id", "in", post_ids)]
        return []

    def action_create_post_account(self):
        """
        Override to handle posting to multiple Facebook accounts.
        """
        self._action_create_post_account()

    def _action_create_post_account(self):
        """
        Override base method to post to ALL accounts, not just [0].
        FIX: Ensure image_ids and video_ids are properly passed to post accounts
        """
        for post in self:
            # DEBUG: Check what images we have
            _logger.debug(
                f"Post {post.id}: {len(post.image_ids)} images,"
                f" {len(post.video_ids)} videos"
            )
            if post.image_ids:
                for i, image in enumerate(post.image_ids):
                    _logger.debug(f"Image {i + 1}: {image.name}, ID: {image.id}")

            post.write(
                {
                    "state": "publishing",
                    "published_date": fields.Datetime.now(),
                    "post_account_ids": post._prepare_post_account_values(),
                }
            )

            for post_account in post.post_account_ids:
                try:
                    _logger.debug(f"Posting to account: {post_account.account_id.name}")
                    _logger.debug(
                        f"Post account has {len(post_account.image_ids)} images,"
                        f" {len(post_account.video_ids)} videos"
                    )

                    post_account.write(
                        {
                            "image_ids": [(6, 0, post.image_ids.ids)],
                            "video_ids": [(6, 0, post.video_ids.ids)],
                        }
                    )

                    post_account._action_post()
                except Exception as e:
                    _logger.error(
                        f"Failed to post to {post_account.account_id.name}: {str(e)}",
                        exc_info=True,
                    )
                    post_account.write(
                        {
                            "state": "failed",
                            "failed_description": f"<p>Error: {str(e)}</p>",
                        }
                    )
                    continue

            post.write(
                {
                    "state": "published",
                }
            )

    @api.depends(
        "post_account_ids.impressions_total",
        "post_account_ids.clicks_total",
        "post_account_ids.spend_amount",
        "post_account_ids.leads_total",
        "post_account_ids.conversions_total",
        "post_account_ids.plays_total",
        "post_account_ids.likes_count",
        "post_account_ids.comments_count",
        "post_account_ids.shares_count",
        "post_account_ids.reach_unique",
    )
    def _compute_facebook_aggregates(self):
        """
        Aggregate Facebook metrics from all post_accounts for this post.
        Used by utm.campaign for campaign-level rollups (Feature #7.2).
        """
        for post in self:
            # Filter only Facebook post accounts
            fb_accounts = post.post_account_ids.filtered(
                lambda pa: pa.media_type == "facebook"
            )

            # Aggregate metrics
            post.impressions = sum(fb_accounts.mapped("impressions_total"))
            post.clicks = sum(fb_accounts.mapped("clicks_total"))
            post.spend = sum(fb_accounts.mapped("spend_amount"))
            post.leads = sum(fb_accounts.mapped("leads_total"))
            post.conversions = sum(fb_accounts.mapped("conversions_total"))
            post.plays_total = sum(fb_accounts.mapped("plays_total"))
            post.likes = sum(fb_accounts.mapped("likes_count"))
            post.comments = sum(fb_accounts.mapped("comments_count"))
            post.shares = sum(fb_accounts.mapped("shares_count"))
            post.reach = sum(fb_accounts.mapped("reach_unique"))

    @api.depends("post_account_ids.fb_content_id")
    def _compute_fb_content_id(self):
        """Get Facebook content ID from first Facebook post account"""
        for post in self:
            fb_account = post.post_account_ids.filtered(
                lambda pa: pa.media_type == "facebook" and pa.fb_content_id
            )[:1]
            post.fb_content_id = fb_account.fb_content_id if fb_account else False

    # === HELPER METHODS ===

    def _render_template_preview(self):
        """Override to pass Facebook account image to preview template"""
        # Check if this post has Facebook accounts
        has_facebook = any(
            account.media_id.media_type == "facebook" for account in self.account_ids
        )

        if not has_facebook:
            return super()._render_template_preview()

        # Render preview for each account
        render_template = ""
        IrQweb = self.env["ir.qweb"]

        for account in self.account_ids:
            values = {
                "media_id": account.media_id,
                "author": account.name,
                "message": self.message,
                "image_ids": self.image_ids[0:2],
                "account_image": account.with_context(
                    bin_size=False
                ).image_128,  # Pass account avatar
            }
            try:
                render_template += """\n\n""" + IrQweb._render(
                    f"social_media_{account.media_id.media_type}.social_network_post_preview",
                    values | self._render_values_preview(),
                )
            except ValueError:
                render_template += """\n\n""" + IrQweb._render(
                    "social_media_base.social_network_post_preview",
                    values | self._render_values_preview(),
                )

        return (
            render_template if render_template else self.env._("No preview available")
        )

    # No override needed - content_type is now handled by base model
