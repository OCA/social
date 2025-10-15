# Copyright 2025 Binhex <https://www.binhex.cloud>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import base64
import logging
from datetime import date, datetime, timedelta

import requests
from werkzeug.urls import url_join

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

from ..social_facebook_utils import _URL_GRAPH_FACEBOOK

_logger = logging.getLogger(__name__)


class SocialAccount(models.Model):
    _inherit = "social.account"

    page_id = fields.Char(string="Facebook Page ID")
    page_name = fields.Char(string="Facebook Page Name")
    page_access_token = fields.Char(string="Page Access Token")
    token_expires_at = fields.Datetime(string="Token Expires At")
    status = fields.Selection(
        [("active", "Active"), ("expired", "Expired"), ("error", "Error")],
        string="Status",
        default="active",
    )
    # Keep legacy fields for backward compatibility during migration
    facebook_page_id = fields.Char(
        related="page_id", readonly=False, store=True, string="Page ID (Legacy)"
    )
    facebook_page_name = fields.Char(
        related="page_name", readonly=False, store=True, string="Page Name (Legacy)"
    )
    facebook_page_token = fields.Char(
        related="page_access_token",
        readonly=False,
        store=True,
        string="Page Token (Legacy)",
    )
    facebook_user_token = fields.Char(string="User Access Token")

    # App credentials (stored per account like LinkedIn/X)
    facebook_app_id = fields.Char(string="App ID")
    facebook_app_secret = fields.Char(string="App Secret")

    # Sync cursor fields
    last_posts_sync_at = fields.Datetime(
        string="Last Posts Sync", help="Last time posts were synced from Facebook"
    )
    last_ads_sync_at = fields.Datetime(
        string="Last Ads Sync", help="Last time ads were synced from Facebook"
    )
    last_reels_sync_at = fields.Datetime(
        string="Last Reels Sync", help="Last time reels were synced from Facebook"
    )

    # Statistics
    posts_count = fields.Integer(
        string="Posts Count", compute="_compute_facebook_posts_count"
    )

    @api.depends("media_type")
    def _compute_facebook_posts_count(self):
        """Compute total posts for this Facebook account"""
        for record in self:
            if record.media_type == "facebook" and record.page_id:
                record.posts_count = self.env["social.post"].search_count(
                    [("fb_post_id", "like", f"{record.page_id}_%")]
                )
            else:
                record.posts_count = 0

    def _fields_account_url(self):
        return super()._fields_account_url() + [
            (
                "page_id",
                "https://www.facebook.com/{}".format(self.page_id),
            )
        ]

    @api.constrains("media_type", "company_id", "page_id")
    def _check_unique_facebook_page(self):
        """Ensure a Facebook page can only be linked once per company"""
        for record in self:
            if record.media_type == "facebook" and record.page_id:
                existing = self.search(
                    [
                        ("id", "!=", record.id),
                        ("media_type", "=", "facebook"),
                        ("page_id", "=", record.page_id),
                        ("company_id", "=", record.company_id.id),
                    ],
                    limit=1,
                )
                if existing:
                    raise ValidationError(
                        _(
                            "A Facebook page with ID '%s' is already linked to this company!"
                        )
                        % record.page_id
                    )

    def unique_account(self, page_id=None):
        """Check if account already exists for this page and company"""
        account_count = self.with_context(active_test=False).search_count(
            [
                ("page_id", "=", page_id or self.page_id),
                ("media_type", "=", "facebook"),
                ("company_id", "=", self.company_id.id or self.env.company.id),
            ]
        )
        if account_count > 0:
            raise ValidationError(
                _(
                    "An account with this information "
                    "already exists; please also check "
                    "archived accounts."
                )
            )

    @api.model
    def _request_facebook(
        self,
        method="GET",
        endpoint=None,
        params=None,
        headers=None,
        timeout=10,
        data=None,
        json_data=None,
    ):
        url = f"{_URL_GRAPH_FACEBOOK}/{endpoint}"
        response = requests.request(
            method=method,
            url=url,
            params=params,
            timeout=timeout,
            headers=headers,
            data=data,
            json=json_data,
        )
        if response.status_code == 200:
            return response.json()
        return response

    def update_account(self):
        res = super().update_account()
        if self.media_type == "facebook":
            # No need to pass app credentials to wizard anymore
            # They are now in system settings
            pass
        return res

    def get_access_token_facebook(
        self, authorization_code, redirect_endpoint_uri, app_id, app_secret
    ):
        """Get access token from Facebook OAuth"""
        _logger.info("Getting Facebook access token...")
        _logger.info("App ID: %s", app_id)

        redirect_url = url_join(self.get_base_url(), redirect_endpoint_uri)
        _logger.info("Redirect URL: %s", redirect_url)

        params = {
            "client_id": app_id,
            "client_secret": app_secret,
            "redirect_uri": redirect_url,
            "code": authorization_code,
        }
        _logger.info("Calling Facebook API: oauth/access_token")
        response = self._request_facebook(endpoint="oauth/access_token", params=params)
        _logger.info("Facebook token API response status: %s",
                    response.status_code if hasattr(response, 'status_code') else 'success')
        return response

    def get_pages_facebook(self, user_access_token):
        _logger.info("Fetching Facebook pages from API...")
        params = {
            "access_token": user_access_token,
        }
        _logger.info("Calling Facebook API: me/accounts")
        response = self._request_facebook(endpoint="me/accounts", params=params)
        _logger.info("Facebook pages API response type: %s", type(response))

        if isinstance(response, dict) and response.get("data"):
            pages = response.get("data", [])
            _logger.info("Successfully retrieved %d pages", len(pages))
            for page in pages:
                _logger.info("  - Page: %s (ID: %s)", page.get("name"), page.get("id"))
            return pages
        else:
            _logger.warning("No pages data in response or error occurred: %s", response)
        return []

    def create_account_facebook(self, selected_page_ids, token):
        """Create Facebook accounts for selected pages only"""
        _logger.info("=" * 80)
        _logger.info("Creating Facebook accounts...")
        _logger.info("Selected page IDs: %s", selected_page_ids)

        if isinstance(token, dict):
            user_access_token = token.get("access_token", False)
            if user_access_token:
                _logger.info("User access token: %s...", user_access_token[:20])
                pages = self.get_pages_facebook(user_access_token)
                # Calculate token expiration (Facebook page tokens don't expire)
                token_expires = datetime.now() + timedelta(days=365 * 10)
                _logger.info("Token expiration set to: %s", token_expires)

                created_count = 0
                updated_count = 0
                skipped_count = 0

                for page in pages:
                    _logger.info("-" * 40)
                    page_id = page.get("id", "")
                    page_name = page.get("name", "")
                    _logger.info("Processing page: %s (ID: %s)", page_name, page_id)

                    # Only create accounts for selected pages
                    if page_id not in selected_page_ids:
                        _logger.info("  Skipped: Not in selected pages")
                        skipped_count += 1
                        continue

                    _logger.info("  Checking for existing account...")
                    existing_account = self.search(
                        [
                            ("page_id", "=", page_id),
                            ("media_type", "=", "facebook"),
                        ],
                        limit=1,
                    )

                    # Get app credentials from wizard if available
                    wizard = self.env["wizard.social.account"].search(
                        [("media_type", "=", "facebook")], order="id desc", limit=1
                    )

                    values_data = {
                        "name": f"[facebook] {page_name}",
                        "username": page_name,
                        "page_id": page_id,
                        "page_name": page_name,
                        "page_access_token": page.get("access_token", ""),
                        "facebook_user_token": user_access_token,
                        "access_token": page.get("access_token", ""),
                        "token_expires_at": token_expires,
                        "status": "active",
                        "media_id": self.env.ref(
                            "social_media_facebook.social_media_facebook"
                        ).id,
                    }

                    # Store app credentials if from wizard
                    if wizard:
                        values_data.update({
                            "facebook_app_id": wizard.facebook_app_id,
                            "facebook_app_secret": wizard.facebook_app_secret,
                        })

                    if not existing_account:
                        _logger.info("  Creating new account...")
                        new_account = self.create(values_data)
                        _logger.info("  ✓ Created account ID: %s", new_account.id)
                        created_count += 1
                    else:
                        _logger.info("  Updating existing account ID: %s", existing_account.id)
                        existing_account.write(values_data)
                        _logger.info("  ✓ Updated account")
                        updated_count += 1

                _logger.info("=" * 80)
                _logger.info("Account creation summary:")
                _logger.info("  Created: %d", created_count)
                _logger.info("  Updated: %d", updated_count)
                _logger.info("  Skipped: %d", skipped_count)
                _logger.info("=" * 80)
        else:
            message_error = f"Creating account: {token}"
            raise ValidationError(message_error)

    def validate_access_token(self):
        res = super().validate_access_token()
        if (
            self.media_id.id
            == self.env.ref("social_media_facebook.social_media_facebook").id
        ):
            if self.token_expires_at and self.token_expires_at < datetime.now():
                self.status = "expired"
                self._notify_user_client(
                    notif_type="social_form_danger",
                    notif_message=_("The access token has expired. Please renew it."),
                    media="facebook",
                    account_name=self.name or "FACEBOOK",
                )
        return res

    def _action_post(self, message, image_ids=None, video_ids=None):
        if self.media_type == "facebook" and self.page_access_token:
            params = {
                "message": message,
                "access_token": self.page_access_token,
            }

            # Handle images
            if image_ids:
                # Facebook API requires uploading photos first, then creating post with photo IDs
                # This is a simplified version
                endpoint = f"{self.page_id}/photos"
                for image in image_ids:
                    files = {"source": base64.b64decode(image.datas)}
                    self._request_facebook(
                        method="POST",
                        endpoint=endpoint,
                        params=params,
                        data=files,
                    )
            else:
                endpoint = f"{self.page_id}/feed"
                response = self._request_facebook(
                    method="POST", endpoint=endpoint, params=params
                )
                if isinstance(response, dict) and response.get("id"):
                    return response.get("id")
        return False

    def _update_posts_statistics(self, post_id, domain):
        statistics = super()._update_posts_statistics(post_id, domain)
        # Implement Facebook statistics update logic here
        return self._get_account_statistics(statistics=statistics)

    def _get_account_statistics(self, statistics=None):
        data = self.search_read(
            [("media_type", "=", "facebook")],
            [
                "name",
                "company_id",
                "media_id",
                "account_url",
                "impression_count",
                "interactions_count",
                "engagement",
                "need_update",
            ],
        )
        if statistics:
            data = list(statistics + data)
        return data

    def action_sync_facebook_content(self):
        """Manual sync button: sync posts, reels, and ads"""
        self.ensure_one()
        if self.media_type != "facebook":
            return

        _logger.info("=" * 80)
        _logger.info("Manual sync started for account: %s", self.name)

        try:
            # Sync posts
            self._sync_facebook_posts()
            # Sync reels
            self._sync_facebook_reels()
            # Sync ads (if configured)
            self._sync_facebook_ads()

            _logger.info("Manual sync completed successfully")
            _logger.info("=" * 80)

            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": "Sync Complete",
                    "message": f"Successfully synced content for {self.name}",
                    "type": "success",
                    "sticky": False,
                },
            }
        except Exception as e:
            _logger.error("Error during manual sync: %s", str(e), exc_info=True)
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": "Sync Failed",
                    "message": f"Error syncing content: {str(e)}",
                    "type": "danger",
                    "sticky": True,
                },
            }

    def _sync_facebook_posts(self):
        """Sync posts from Facebook Page with detailed metrics

        API Mapping per Feature #3 requirements:
        - Likes: /{POST_ID}?fields=likes.summary(true)
        - Reactions by type: /{POST_ID}/insights?metric=post_reactions_by_type_total
        - Comments: /{POST_ID}?fields=comments.summary(true)
        - Shares: /{POST_ID}?fields=shares
        - Impressions: /{POST_ID}/insights?metric=post_impressions
        - Reach (unique): /{POST_ID}/insights?metric=post_impressions_unique
        - Clicks: /{POST_ID}/insights?metric=post_clicks
        """
        self.ensure_one()
        if not self.page_id or not self.page_access_token:
            _logger.warning("No page_id or access token for account %s", self.name)
            return

        _logger.info("Syncing posts for page: %s", self.page_name)

        # Fetch posts with basic fields
        fields = (
            "id,message,created_time,permalink_url,"
            "attachments{media_type,media,url},"
            "likes.summary(true),comments.summary(true),shares,"
            "insights.metric(post_impressions,post_impressions_unique,"
            "post_reactions_by_type_total,post_clicks)"
        )
        params = {
            "access_token": self.page_access_token,
            "fields": fields,
            "limit": 100,
        }

        # Incremental sync using since parameter
        if self.last_posts_sync_at:
            params["since"] = int(self.last_posts_sync_at.timestamp())

        endpoint = f"{self.page_id}/posts"
        response = self._request_facebook(endpoint=endpoint, params=params)

        if isinstance(response, dict) and response.get("data"):
            posts_data = response.get("data", [])
            _logger.info("Retrieved %d posts from Facebook", len(posts_data))

            created_count = 0
            updated_count = 0

            for post_data in posts_data:
                try:
                    fb_content_id = post_data.get("id")

                    # Deduplication check: (fb_content_id, page_id)
                    existing_post = self.env["social.post"].search(
                        [
                            ("fb_content_id", "=", fb_content_id),
                            "|",
                            ("fb_content_id", "=", fb_content_id),
                            ("fb_post_id", "=", fb_content_id),  # Legacy compatibility
                        ],
                        limit=1,
                    )

                    # Parse attachments
                    media_url = None
                    media_type_val = None
                    attachments = post_data.get("attachments", {}).get("data", [])
                    if attachments:
                        first_attachment = attachments[0]
                        media_type_val = first_attachment.get("media_type")
                        if "media" in first_attachment:
                            media_url = first_attachment["media"].get("image", {}).get("src")

                    # Parse summary fields
                    likes_count = post_data.get("likes", {}).get("summary", {}).get("total_count", 0)
                    comments_count = post_data.get("comments", {}).get("summary", {}).get("total_count", 0)
                    shares_count = post_data.get("shares", {}).get("count", 0)

                    # Parse insights
                    insights = post_data.get("insights", {}).get("data", [])
                    impressions_total = 0
                    reach_unique = 0
                    clicks_total = 0
                    reactions_by_type = {}

                    for insight in insights:
                        metric_name = insight.get("name")
                        values = insight.get("values", [])
                        if values:
                            value = values[0].get("value", 0)
                            if metric_name == "post_impressions":
                                impressions_total = value
                            elif metric_name == "post_impressions_unique":
                                reach_unique = value
                            elif metric_name == "post_reactions_by_type_total":
                                if isinstance(value, dict):
                                    reactions_by_type = value
                            elif metric_name == "post_clicks":
                                clicks_total = value

                    # Build metrics data
                    import json
                    metrics_data = {
                        "name": post_data.get("message", "")[:100] or f"Post {fb_content_id}",
                        "message": post_data.get("message", ""),
                        "fb_content_id": fb_content_id,
                        "fb_content_type": "post",
                        "permalink_url": post_data.get("permalink_url"),
                        "created_time": post_data.get("created_time"),
                        "media_url": media_url,
                        "media_type": media_type_val,
                        # Updated field names per Feature #3
                        "likes_count": likes_count,
                        "reactions_by_type_json": json.dumps(reactions_by_type) if reactions_by_type else None,
                        "comments_count": comments_count,
                        "shares_count": shares_count,
                        "impressions_total": impressions_total,
                        "reach_unique": reach_unique,
                        "clicks_total": clicks_total,
                        "media_id": self.media_id.id,
                    }

                    if existing_post:
                        existing_post.write_metrics_snapshot(metrics_data)
                        updated_count += 1
                    else:
                        post = self.env["social.post"].create(metrics_data)
                        post.write_metrics_snapshot(metrics_data)
                        created_count += 1

                except Exception as e:
                    _logger.error("Error processing post %s: %s", post_data.get("id"), str(e), exc_info=True)
                    continue

            self.last_posts_sync_at = fields.Datetime.now()
            _logger.info("Posts sync completed: %d created, %d updated", created_count, updated_count)

        else:
            _logger.warning("No posts data in response: %s", response)

    def _sync_facebook_reels(self):
        """Sync reels/videos from Facebook Page with detailed metrics

        API Mapping per Feature #3 requirements:
        - Total plays: /{VIDEO_ID}/insights?metric=total_video_views
        - Unique plays: /{VIDEO_ID}/insights?metric=total_video_views_unique
        - Watch time: /{VIDEO_ID}/insights?metric=total_video_view_time
        - Avg watch time: /{VIDEO_ID}/insights?metric=avg_time_watched
        - Completion rate: /{VIDEO_ID}/insights?metric=total_video_complete_views
        - Shares: /{VIDEO_ID}?fields=shares (optional)
        """
        self.ensure_one()
        if not self.page_id or not self.page_access_token:
            _logger.warning("No page_id or access token for account %s", self.name)
            return

        _logger.info("Syncing reels for page: %s", self.page_name)

        # Fetch videos with extended insights
        fields = (
            "id,title,description,created_time,permalink_url,shares,"
            "video_insights.metric(total_video_views,total_video_views_unique,"
            "total_video_view_time,total_video_complete_views,avg_time_watched)"
        )
        params = {
            "access_token": self.page_access_token,
            "fields": fields,
            "limit": 100,
        }

        # Incremental sync
        if self.last_reels_sync_at:
            params["since"] = int(self.last_reels_sync_at.timestamp())

        endpoint = f"{self.page_id}/videos"
        response = self._request_facebook(endpoint=endpoint, params=params)

        if isinstance(response, dict) and response.get("data"):
            videos_data = response.get("data", [])
            _logger.info("Retrieved %d videos/reels from Facebook", len(videos_data))

            created_count = 0
            updated_count = 0

            for video_data in videos_data:
                try:
                    fb_content_id = video_data.get("id")

                    # Deduplication check
                    existing_post = self.env["social.post"].search(
                        [
                            "|",
                            ("fb_content_id", "=", fb_content_id),
                            ("fb_post_id", "=", fb_content_id),  # Legacy
                        ],
                        limit=1,
                    )

                    # Parse video insights
                    insights = video_data.get("video_insights", {}).get("data", [])
                    plays_total = 0
                    plays_unique = 0
                    watch_time_sec = 0
                    completed_views = 0
                    avg_watch_time = 0.0

                    for insight in insights:
                        metric_name = insight.get("name")
                        values = insight.get("values", [])
                        if values:
                            value = values[0].get("value", 0)
                            if metric_name == "total_video_views":
                                plays_total = value
                            elif metric_name == "total_video_views_unique":
                                plays_unique = value
                            elif metric_name == "total_video_view_time":
                                watch_time_sec = value
                            elif metric_name == "total_video_complete_views":
                                completed_views = value
                            elif metric_name == "avg_time_watched":
                                avg_watch_time = value

                    # Parse shares (optional)
                    shares_count = video_data.get("shares", {}).get("count", 0)

                    # Calculate completion rate
                    completion_rate_pct = 0.0
                    if plays_total > 0:
                        completion_rate_pct = (completed_views / plays_total) * 100

                    # Build metrics data
                    import json
                    metrics_data = {
                        "name": video_data.get("title", "")[:100] or f"Video {fb_content_id}",
                        "message": video_data.get("description", ""),
                        "fb_content_id": fb_content_id,
                        "fb_content_type": "reel",
                        "permalink_url": video_data.get("permalink_url"),
                        "created_time": video_data.get("created_time"),
                        "media_type": "video",
                        # Updated field names per Feature #3
                        "plays_total": plays_total,
                        "plays_unique": plays_unique,
                        "watch_time_sec": watch_time_sec,
                        "shares_count": shares_count,
                        "media_id": self.media_id.id,
                    }

                    if existing_post:
                        existing_post.write_metrics_snapshot(metrics_data)
                        updated_count += 1
                    else:
                        post = self.env["social.post"].create(metrics_data)
                        post.write_metrics_snapshot(metrics_data)
                        created_count += 1

                except Exception as e:
                    _logger.error("Error processing video %s: %s", video_data.get("id"), str(e), exc_info=True)
                    continue

            self.last_reels_sync_at = fields.Datetime.now()
            _logger.info("Reels sync completed: %d created, %d updated", created_count, updated_count)

        else:
            _logger.warning("No videos data in response: %s", response)

    def _sync_facebook_ads(self):
        """Sync ads insights from Facebook Marketing API

        API Mapping per Feature #3 requirements:
        - From /{AD_ID}/insights:
          - impressions_total ← impressions
          - reach_unique ← reach
          - clicks_total ← clicks
          - ctr_pct ← ctr
          - spend_amount ← spend (+ currency)
          - leads_total ← Σ actions[action_type='lead']
          - conversions_total ← Σ actions for configured types
          - compute cpl_amount

        Note: Requires ad account access and Marketing API permissions
        """
        self.ensure_one()
        _logger.info("Syncing ads for page: %s", self.page_name)

        # TODO: Implement ad account lookup
        # For now, we'll check if the page has an associated ad account
        # This typically requires getting the ad_account_id from the page
        # or from user configuration

        # Placeholder: Check for ad account ID
        # In a full implementation, you would:
        # 1. Get ad account(s) for this page
        # 2. Fetch ads from act_{ad_account_id}/ads
        # 3. Fetch insights for each ad

        _logger.warning(
            "Ad sync requires Marketing API setup. "
            "Please configure ad_account_id for page: %s",
            self.page_name,
        )

        # Example implementation structure (commented out):
        # ad_account_id = self.fb_ad_account_id  # Would need to add this field
        # if not ad_account_id:
        #     self.last_ads_sync_at = fields.Datetime.now()
        #     return
        #
        # fields = "id,name,status,creative"
        # params = {
        #     "access_token": self.page_access_token,
        #     "fields": fields,
        #     "limit": 100,
        # }
        #
        # if self.last_ads_sync_at:
        #     params["filtering"] = json.dumps([{
        #         "field": "updated_time",
        #         "operator": "GREATER_THAN",
        #         "value": int(self.last_ads_sync_at.timestamp()),
        #     }])
        #
        # endpoint = f"act_{ad_account_id}/ads"
        # response = self._request_facebook(endpoint=endpoint, params=params)
        #
        # if isinstance(response, dict) and response.get("data"):
        #     ads_data = response.get("data", [])
        #     _logger.info("Retrieved %d ads from Facebook", len(ads_data))
        #
        #     for ad_data in ads_data:
        #         try:
        #             fb_ad_id = ad_data.get("id")
        #
        #             # Fetch insights for this ad
        #             insights_fields = (
        #                 "impressions,reach,clicks,ctr,spend,currency,"
        #                 "actions,cost_per_action_type"
        #             )
        #             insights_params = {
        #                 "access_token": self.page_access_token,
        #                 "fields": insights_fields,
        #                 "level": "ad",
        #             }
        #             insights_endpoint = f"{fb_ad_id}/insights"
        #             insights_response = self._request_facebook(
        #                 endpoint=insights_endpoint, params=insights_params
        #             )
        #
        #             insights_data = insights_response.get("data", [{}])[0]
        #
        #             # Parse actions for leads and conversions
        #             actions = insights_data.get("actions", [])
        #             leads_total = sum(
        #                 int(action.get("value", 0))
        #                 for action in actions
        #                 if action.get("action_type") == "lead"
        #             )
        #             conversions_total = sum(
        #                 int(action.get("value", 0))
        #                 for action in actions
        #                 if action.get("action_type") in ["offsite_conversion", "onsite_conversion"]
        #             )
        #
        #             # Build metrics data
        #             metrics_data = {
        #                 "name": ad_data.get("name", "")[:100] or f"Ad {fb_ad_id}",
        #                 "fb_content_id": fb_ad_id,
        #                 "fb_ad_id": fb_ad_id,
        #                 "fb_content_type": "ad",
        #                 "ad_name": ad_data.get("name"),
        #                 "impressions_total": int(insights_data.get("impressions", 0)),
        #                 "reach_unique": int(insights_data.get("reach", 0)),
        #                 "clicks_total": int(insights_data.get("clicks", 0)),
        #                 "ctr_pct": float(insights_data.get("ctr", 0)),
        #                 "spend_amount": float(insights_data.get("spend", 0)),
        #                 "currency": insights_data.get("currency", "USD"),
        #                 "leads_total": leads_total,
        #                 "conversions_total": conversions_total,
        #                 "media_id": self.media_id.id,
        #             }
        #
        #             # Deduplication
        #             existing_post = self.env["social.post"].search(
        #                 [("fb_ad_id", "=", fb_ad_id)], limit=1
        #             )
        #
        #             if existing_post:
        #                 existing_post.write_metrics_snapshot(metrics_data)
        #             else:
        #                 post = self.env["social.post"].create(metrics_data)
        #                 post.write_metrics_snapshot(metrics_data)
        #
        #         except Exception as e:
        #             _logger.error("Error processing ad %s: %s", ad_data.get("id"), str(e))
        #             continue

        self.last_ads_sync_at = fields.Datetime.now()
        _logger.info("Ads sync completed (placeholder) for page: %s", self.page_name)

    def _cron_sync_facebook_content(self):
        """Scheduled action to sync all Facebook accounts"""
        accounts = self.search([("media_type", "=", "facebook"), ("status", "=", "active")])
        _logger.info("Cron: Starting sync for %d Facebook accounts", len(accounts))

        for account in accounts:
            try:
                account.action_sync_facebook_content()
            except Exception as e:
                _logger.error("Error syncing account %s: %s", account.name, str(e))
                continue

        _logger.info("Cron: Sync completed for all accounts")
