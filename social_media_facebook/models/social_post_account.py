# Copyright 2025 Kencove (https://www.kencove.com/)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import json
import logging

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class SocialPostAccount(models.Model):
    _inherit = "social.post.account"
    _order = "created_time desc"

    # ===== FACEBOOK-SPECIFIC FIELDS =====
    # These fields are specific to Facebook posts published on this account

    # Facebook content ID (content_type is now generic in base module)
    fb_content_id = fields.Char(
        string="Facebook Content ID",
        index=True,
        help="Unique identifier for FB content (post/reel/ad)",
    )

    # Override comment_count to make it computed for Facebook
    comment_count = fields.Integer(
        compute="_compute_facebook_comment_count",
        store=True,
        compute_sudo=True,
    )
    facebook_post_id = fields.Char(
        string="Facebook Post ID",
        help="Alias for fb_content_id for backward compatibility",
    )
    # fb_content_type removed - using base model's content_type field instead
    permalink_url = fields.Char(string="Permalink URL", help="Direct URL to the post")
    fb_video_url = fields.Char(
        string="Facebook Video URL",
        help="Direct URL to the Facebook video file (for reels/videos)",
    )
    created_time = fields.Datetime(help="When the post was created on Facebook")
    last_sync_at = fields.Datetime(
        string="Last Synced At", help="Last time this post was synced from Facebook"
    )

    # Ads-only fields
    fb_ad_id = fields.Char(string="Facebook Ad ID", index=True, help="Facebook Ad ID")
    fb_adset_id = fields.Char(string="Facebook AdSet ID", help="Facebook AdSet ID")
    fb_campaign_id = fields.Char(
        string="Facebook Campaign ID", help="Facebook Campaign ID"
    )
    ad_name = fields.Char(help="Name of the ad")
    currency = fields.Char(default="USD", help="Currency code")

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
    spend_amount = fields.Float(default=0.0, digits=(16, 2), help="Total ad spend")
    ctr_pct = fields.Float(
        string="CTR %", default=0.0, digits=(5, 2), help="Click-through rate %"
    )
    leads_total = fields.Integer(
        string="Leads", default=0, help="Total leads generated"
    )
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
        default=0,
        help="Number of views that watched to completion",
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
    metrics_updated_at = fields.Datetime(help="When metrics_json was last updated")

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

    @api.depends("post_id")
    def _compute_facebook_comment_count(self):
        """Compute total comment count including parent comments and all replies"""
        for record in self:
            if record.media_type == "facebook" and record.post_id:
                # Count all comments (parent + replies) for this post
                total_comments = self.env["social.comment"].search_count(
                    [("post_id", "=", record.post_id.id)]
                )
                record.comment_count = total_comments
            else:
                record.comment_count = 0

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
                record.engagement_rate_pct = (
                    numerator / record.impressions_total
                ) * 100
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
                record.completion_rate_pct = (
                    record.completed_views / record.plays_total
                ) * 100
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

    # === SQL CONSTRAINTS ===
    _sql_constraints = [
        (
            "fb_content_unique",
            "unique(fb_content_id)",
            "This Facebook content has already been synced!",
        ),
    ]

    def _action_post(self):
        """Publish post to Facebook and sync back metadata"""
        self.ensure_one()

        # DEBUG: Check what we're actually receiving
        _logger.debug(
            f"_action_post: Post {self.post_id.id}, Account: {self.account_id.name}"
        )
        _logger.debug(f"Images: {self.image_ids.ids}, Count: {len(self.image_ids)}")
        _logger.debug(f"Videos: {self.video_ids.ids}, Count: {len(self.video_ids)}")

        if self.image_ids:
            for i, image in enumerate(self.image_ids):
                _logger.debug(
                    f"Image {i+1}: {image.name}, ID: {image.id}, "
                    f"Data: {'Yes' if image.datas else 'No'}"
                )

        _logger.debug(f"Starting _action_post for {self.id} - Account: \
            {self.account_id.name}, Media: {self.account_id.media_type}")

        if self.account_id.media_type == "facebook":
            try:
                _logger.debug(f"Setting state to 'posting' for account {self.id}")
                self.write({"state": "posting"})
                _logger.debug(
                    "State set successfully. Now calling account._action_post()"
                )

                # content_type is now stored on base model
                post_id = self.account_id._action_post(
                    message=self.message,
                    image_ids=self.image_ids,
                    video_ids=self.video_ids,
                )
                _logger.debug(f"account._action_post() returned post_id: {post_id}")

                if post_id:
                    _logger.debug(f"Successfully got post_id {post_id}, \
                        updating state to 'posted'")
                    # Write basic post info first
                    self.write(
                        {
                            "facebook_post_id": post_id,
                            "fb_content_id": post_id,
                            "post_account_url": f"https://www.facebook.com/{post_id}",
                            "published_date": fields.Datetime.now(),
                            "state": "posted",
                            "failed_description": False,  # Clear any previous errors
                        }
                    )
                    _logger.debug(
                        f"Successfully updated account {self.id} to 'posted' state"
                    )

                    # Sync back the post data from Facebook to get analytics
                    _logger.debug(
                        f"Syncing back published post {post_id} to get Facebook data..."
                    )
                    self._sync_published_post_from_facebook(post_id)
                    _logger.debug(f"Sync completed for post {post_id}")
                else:
                    _logger.warning("No post_id returned from account._action_post()")
                    self.write(
                        {
                            "state": "failed",
                            "failed_description": "<p>Failed to post on Facebook. \
                                No post ID returned from API.</p>",
                        }
                    )
            except Exception as e:
                error_msg = str(e)
                _logger.error(
                    f"Exception in _action_post for account \
                    {self.id}: {error_msg}",
                    exc_info=True,
                )
                self.write(
                    {
                        "state": "failed",
                        "failed_description": (
                            f"<p><strong>Error:</strong>" f" {error_msg}</p>"
                        ),
                    }
                )
        else:
            # For non-Facebook accounts, call parent
            _logger.debug("Non-Facebook account, calling super()._action_post()")
            return super()._action_post()

    def _sync_published_post_from_facebook(self, fb_post_id):
        """Sync back a newly published post from Facebook to populate metrics

        This allows the Facebook Analytics tab to appear and show metrics for
        Odoo-created posts.
        Data is stored on social.post.account (this record), not on social.post.

        Args:
            fb_post_id: The Facebook post ID returned from publishing
        """
        self.ensure_one()
        if not self.account_id or self.account_id.media_type != "facebook":
            return

        try:
            # Fetch post data from Facebook with metrics
            fields_str = (
                "id,message,created_time,permalink_url,"
                "attachments{media_type,media,url},"
                "likes.summary(true),comments.summary(true),shares,"
                "insights.metric(post_impressions,post_impressions_unique,"
                "post_reactions_by_type_total,post_clicks)"
            )
            params = {
                "access_token": self.account_id.page_access_token,
                "fields": fields_str,
            }

            response = self.account_id._request_facebook(
                endpoint=fb_post_id, params=params
            )

            if isinstance(response, dict) and response.get("id"):
                _logger.debug(
                    f"Successfully fetched post data from Facebook for {fb_post_id}"
                )

                # Extract metrics
                likes_count = (
                    response.get("likes", {}).get("summary", {}).get("total_count", 0)
                )
                comments_count = (
                    response.get("comments", {})
                    .get("summary", {})
                    .get("total_count", 0)
                )
                shares_count = response.get("shares", {}).get("count", 0)

                insights = response.get("insights", {}).get("data", [])
                impressions_total = 0
                reach_unique = 0
                clicks_total = 0

                for insight in insights:
                    metric_name = insight.get("name")
                    values = insight.get("values", [])
                    if values:
                        value = values[0].get("value", 0)
                        if metric_name == "post_impressions":
                            impressions_total = value
                        elif metric_name == "post_impressions_unique":
                            reach_unique = value
                        elif metric_name == "post_clicks":
                            clicks_total = value

                # Update THIS social.post.account record with Facebook data
                self.write(
                    {
                        "fb_content_id": response.get("id"),
                        "permalink_url": response.get("permalink_url"),
                        "created_time": self.account_id._parse_facebook_datetime(
                            response.get("created_time")
                        ),
                        "likes_count": likes_count,
                        "comments_count": comments_count,
                        "shares_count": shares_count,
                        "impressions_total": impressions_total,
                        "reach_unique": reach_unique,
                        "clicks_total": clicks_total,
                        "last_sync_at": fields.Datetime.now(),
                        # Also update base fields for display
                        "like_count": likes_count,
                        "comment_count": comments_count,
                        "share_count": shares_count,
                        "view_count": impressions_total,
                    }
                )

                _logger.debug(
                    f"Updated social.post.account {self.id} with Facebook data"
                )
                _logger.debug(f"  fb_content_id: {response.get('id')}")
                _logger.debug(
                    f"  Likes: {likes_count}, "
                    f"Comments: {comments_count}, Shares: {shares_count}"
                )
            else:
                _logger.warning(f"Failed to fetch post data from Facebook: {response}")

        except Exception as e:
            _logger.error(f"Error syncing published post from Facebook: {str(e)}")

    def action_open_external_post(self):
        """Open the external Facebook post URL in a new browser tab"""
        self.ensure_one()
        if self.post_account_url:
            return {
                "type": "ir.actions.act_url",
                "url": self.post_account_url,
                "target": "new",
            }
        return False

    def get_comments(self):
        """Retrieve comments for this Facebook post

        Returns:
            dict: {"success": bool, "data": list of comment dicts}
        """
        self.ensure_one()

        # Only process if this is a Facebook post
        if self.media_type != "facebook" or not self.fb_content_id:
            return {"success": False, "data": [], "message": "Not a Facebook post"}

        try:
            # Fetch comments from database (already synced from Facebook)
            comments = self.env["social.comment"].search(
                [
                    ("post_id", "=", self.post_id.id),
                    ("parent_id", "=", False),  # Only top-level comments
                ],
                order="created_time desc",
            )

            comment_list = []
            for comment in comments:
                comment_data = {
                    "id": comment.id,
                    "comment_id": comment.comment_id,
                    "author": comment.author_name,
                    "author_id": comment.author_id,
                    "author_image": comment.author_avatar or False,
                    "message": comment.message,
                    "created_time": comment.created_time.isoformat()
                    if comment.created_time
                    else False,
                    "is_replied": comment.is_replied,
                    "is_hidden": comment.is_hidden,
                    "reply_count": comment.reply_count,
                    "replies": [],
                }

                # Add replies
                for reply in comment.reply_ids:
                    reply_data = {
                        "id": reply.id,
                        "comment_id": reply.comment_id,
                        "author": reply.author_name,
                        "author_id": reply.author_id,
                        "author_image": reply.author_avatar or False,
                        "message": reply.message,
                        "created_time": reply.created_time.isoformat()
                        if reply.created_time
                        else False,
                        "is_replied": reply.is_replied,
                        "is_hidden": reply.is_hidden,
                    }
                    comment_data["replies"].append(reply_data)

                comment_list.append(comment_data)

            return {
                "success": True,
                "data": comment_list,
                "message": f"Retrieved {len(comment_list)} comments",
            }

        except Exception as e:
            _logger.error(f"Failed to get comments for post {self.id}: {str(e)}")
            return {
                "success": False,
                "data": [],
                "message": f"Error retrieving comments: {str(e)}",
            }

    def create_comment(self, post_data, context=None):
        """Post a reply to a Facebook comment

        Args:
            post_data: dict with keys:
                - "comment_id": ID of the comment to reply to
                    (optional, if replying to a comment)
                - "message": The reply text
                - "post_account_id": This post account ID

        Returns:
            dict: {"success": bool, "message": str, "comment_id": str}
        """
        self.ensure_one()

        if self.media_type != "facebook":
            return {"success": False, "message": "Not a Facebook post"}

        try:
            message = post_data.get("message", "").strip()
            parent_comment_id = post_data.get("comment_id")  # Facebook comment ID

            if not message:
                return {"success": False, "message": "Message cannot be empty"}

            # Get the account to access Facebook API
            account = self.account_id

            # Reply to a specific comment
            if parent_comment_id:
                response = account._reply_to_facebook_comment(
                    parent_comment_id, message
                )
                if response and response.get("id"):
                    # Mark parent comment as replied in database
                    parent_comment = self.env["social.comment"].search(
                        [("comment_id", "=", parent_comment_id)], limit=1
                    )
                    if parent_comment:
                        parent_comment.write({"is_replied": True})

                    return {
                        "success": True,
                        "message": "Reply posted successfully",
                        "comment_id": response.get("id"),
                    }
                else:
                    return {"success": False, "message": "Failed to post reply"}

            # Comment on the post itself
            else:
                # Post comment directly to the post
                if not self.fb_content_id:
                    return {"success": False, "message": "No Facebook content ID"}

                params = {
                    "message": message,
                    "access_token": account.page_access_token,
                }

                endpoint = f"{self.fb_content_id}/comments"
                response = account._request_facebook(
                    method="POST",
                    endpoint=endpoint,
                    params=params,
                )

                if isinstance(response, dict) and response.get("id"):
                    return {
                        "success": True,
                        "message": "Comment posted successfully",
                        "comment_id": response.get("id"),
                    }
                else:
                    return {"success": False, "message": "Failed to post comment"}

        except Exception as e:
            _logger.error(f"Failed to create comment: {str(e)}")
            return {"success": False, "message": f"Error: {str(e)}"}

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

    def action_post_comment(self, message):
        """Post a new parent comment to this Facebook post

        Args:
            message: The comment text to post

        Returns:
            dict: {"success": bool, "message": str, "comment_id": str}
        """
        self.ensure_one()

        if self.media_type != "facebook":
            return {"success": False, "message": "Not a Facebook post"}

        if not message or not message.strip():
            return {"success": False, "message": "Message cannot be empty"}

        if not self.fb_content_id:
            return {"success": False, "message": "No Facebook content ID"}

        try:
            # Get the account to access Facebook API
            account = self.account_id

            # Post comment to Facebook
            params = {
                "message": message.strip(),
                "access_token": account.page_access_token,
            }

            endpoint = f"{self.fb_content_id}/comments"
            response = account._request_facebook(
                method="POST",
                endpoint=endpoint,
                params=params,
            )

            if isinstance(response, dict) and response.get("id"):
                comment_id = response.get("id")

                # Create the comment record in Odoo
                self.env["social.comment"].create(
                    {
                        "post_id": self.post_id.id,
                        "comment_id": comment_id,
                        "parent_id": False,  # This is a parent comment
                        "message": message.strip(),
                        "author_name": self.env.user.name,
                        "author_id": str(account.page_id or ""),
                        "created_time": fields.Datetime.now(),
                        "is_replied": False,
                        "is_hidden": False,
                    }
                )

                return {
                    "success": True,
                    "message": "Comment posted successfully",
                    "comment_id": comment_id,
                }
            else:
                return {
                    "success": False,
                    "message": "Failed to post comment to Facebook",
                }

        except Exception as e:
            _logger.error(f"Failed to post comment: {str(e)}")
            return {"success": False, "message": f"Error: {str(e)}"}
