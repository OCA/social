# Copyright 2025 Binhex <https://www.binhex.cloud>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import base64
import json
from datetime import date, datetime, timedelta

import requests
from dateutil import parser as dateutil_parser
from werkzeug.urls import url_join

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

from ..social_facebook_utils import _URL_GRAPH_FACEBOOK


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
    facebook_user_token = fields.Char(string="User Access Token")

    # App credentials (stored per account like LinkedIn/X)
    facebook_app_id = fields.Char(string="App ID")
    facebook_app_secret = fields.Char(string="App Secret")

    # Ad account for Marketing API access
    fb_ad_account_id = fields.Char(
        string="Ad Account ID",
        help="Facebook Ad Account ID (format: act_123456789) for syncing ad insights",
    )

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
                    [("fb_content_id", "like", f"{record.page_id}_%")]
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
        print("Getting Facebook access token...")
        print(f"App ID: {app_id}")

        redirect_url = url_join(self.get_base_url(), redirect_endpoint_uri)
        print(f"Redirect URL: {redirect_url}")

        params = {
            "client_id": app_id,
            "client_secret": app_secret,
            "redirect_uri": redirect_url,
            "code": authorization_code,
        }
        print("Calling Facebook API: oauth/access_token")
        response = self._request_facebook(endpoint="oauth/access_token", params=params)
        print(f"Facebook token API response status: {response.status_code if hasattr(response, 'status_code') else 'success'}")
        return response

    def get_pages_facebook(self, user_access_token):
        print("Fetching Facebook pages from API...")
        params = {
            "access_token": user_access_token,
        }
        print("Calling Facebook API: me/accounts")
        response = self._request_facebook(endpoint="me/accounts", params=params)
        print(f"Facebook pages API response type: {type(response)}")

        if isinstance(response, dict) and response.get("data"):
            pages = response.get("data", [])
            print(f"Successfully retrieved {len(pages)} pages")
            for page in pages:
                print(f"  - Page: {page.get('name')} (ID: {page.get('id')})")
            return pages
        else:
            print(f"WARNING: No pages data in response or error occurred: {response}")
        return []

    def create_account_facebook(self, selected_page_ids, token):
        """Create Facebook accounts for selected pages only"""
        print("=" * 80)
        print("Creating Facebook accounts...")
        print(f"Selected page IDs: {selected_page_ids}")

        if isinstance(token, dict):
            user_access_token = token.get("access_token", False)
            if user_access_token:
                print(f"User access token: {user_access_token[:20]}...")
                pages = self.get_pages_facebook(user_access_token)
                # Calculate token expiration (Facebook page tokens don't expire)
                token_expires = datetime.now() + timedelta(days=365 * 10)
                print(f"Token expiration set to: {token_expires}")

                created_count = 0
                updated_count = 0
                skipped_count = 0

                for page in pages:
                    print("-" * 40)
                    page_id = page.get("id", "")
                    page_name = page.get("name", "")
                    print(f"Processing page: {page_name} (ID: {page_id})")

                    # Only create accounts for selected pages
                    if page_id not in selected_page_ids:
                        print("  Skipped: Not in selected pages")
                        skipped_count += 1
                        continue

                    print("  Checking for existing account...")
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
                        print("  Creating new account...")
                        new_account = self.create(values_data)
                        print(f"  ✓ Created account ID: {new_account.id}")
                        created_count += 1
                    else:
                        print(f"  Updating existing account ID: {existing_account.id}")
                        existing_account.write(values_data)
                        print("  ✓ Updated account")
                        updated_count += 1

                print("=" * 80)
                print("Account creation summary:")
                print(f"  Created: {created_count}")
                print(f"  Updated: {updated_count}")
                print(f"  Skipped: {skipped_count}")
                print("=" * 80)
        else:
            message_error = f"Creating account: {token}"
            raise ValidationError(message_error)

    def create_account_facebook_from_wizard(self, pages_data, user_access_token, wizard_social_account):
        """Create Facebook accounts using data directly from wizard (no re-fetch)

        Args:
            pages_data: List of dicts with page info [{"id": ..., "name": ..., "access_token": ...}]
            user_access_token: Facebook user access token
            wizard_social_account: wizard.social.account record with app credentials

        Returns:
            list: IDs of created/updated accounts
        """
        print("=" * 80)
        print("Creating Facebook accounts from wizard data...")
        print(f"Pages to create: {len(pages_data)}")

        # Calculate token expiration (Facebook page tokens don't expire)
        token_expires = datetime.now() + timedelta(days=365 * 10)

        created_count = 0
        updated_count = 0
        account_ids = []

        for page in pages_data:
            print("-" * 40)
            page_id = page.get("id", "")
            page_name = page.get("name", "")
            print(f"Processing page: {page_name} (ID: {page_id})")

            # Check for existing account
            print("  Checking for existing account...")
            existing_account = self.search(
                [
                    ("page_id", "=", page_id),
                    ("media_type", "=", "facebook"),
                ],
                limit=1,
            )

            values_data = {
                "name": page_name,
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

            # Download and store Facebook page profile picture
            print("  Downloading page profile picture...")
            page_picture = self._download_facebook_page_picture(page_id, page.get("access_token", ""))
            if page_picture:
                values_data["image_1920"] = page_picture
                print("  ✓ Page profile picture downloaded")

            # Store app credentials if from wizard
            if wizard_social_account:
                values_data.update({
                    "facebook_app_id": wizard_social_account.facebook_app_id,
                    "facebook_app_secret": wizard_social_account.facebook_app_secret,
                })
                print("  Storing app credentials from wizard")

            if not existing_account:
                print("  Creating new account...")
                new_account = self.create(values_data)
                print(f"  ✓ Created account ID: {new_account.id}")
                account_ids.append(new_account.id)
                created_count += 1
            else:
                print(f"  Updating existing account ID: {existing_account.id}")
                existing_account.write(values_data)
                print("  ✓ Updated account")
                account_ids.append(existing_account.id)
                updated_count += 1

        # Delete the wizard_social_account after successful account creation
        if wizard_social_account:
            print("Deleting wizard.social.account after successful creation")
            wizard_social_account.unlink()

        print("=" * 80)
        print("Account creation summary:")
        print(f"  Created: {created_count}")
        print(f"  Updated: {updated_count}")
        print("=" * 80)

        return account_ids

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

    def action_refresh_facebook_token(self):
        """Feature #1.2: Refresh Facebook access token

        This method attempts to exchange the current token for a new long-lived token
        and refresh the page access token.
        """
        self.ensure_one()
        if self.media_type != "facebook":
            return

        if not self.facebook_app_id or not self.facebook_app_secret:
            raise UserError(_(
                "App credentials not configured. "
                "Please configure Facebook App ID and App Secret in settings."
            ))

        if not self.facebook_user_token:
            raise UserError(_(
                "No user access token available. "
                "Please re-authenticate by updating the account."
            ))

        print(f"Refreshing token for Facebook account: {self.name}")

        try:
            # Step 1: Exchange short-lived token for long-lived token
            params = {
                "grant_type": "fb_exchange_token",
                "client_id": self.facebook_app_id,
                "client_secret": self.facebook_app_secret,
                "fb_exchange_token": self.facebook_user_token,
            }

            response = self._request_facebook(
                endpoint="oauth/access_token",
                params=params
            )

            if isinstance(response, dict) and response.get("access_token"):
                new_user_token = response.get("access_token")
                print("Successfully obtained new user access token")

                # Step 2: Get fresh page access token using new user token
                pages = self.get_pages_facebook(new_user_token)

                # Find the page matching this account
                matching_page = None
                for page in pages:
                    if page.get("id") == self.page_id:
                        matching_page = page
                        break

                if matching_page:
                    new_page_token = matching_page.get("access_token")

                    # Update tokens
                    self.write({
                        "facebook_user_token": new_user_token,
                        "page_access_token": new_page_token,
                        "access_token": new_page_token,
                        "token_expires_at": datetime.now() + timedelta(days=60),
                        "status": "active",
                    })

                    print(f"Token refreshed successfully for: {self.name}")

                    return {
                        "type": "ir.actions.client",
                        "tag": "display_notification",
                        "params": {
                            "title": _("Token Refreshed"),
                            "message": _("Access token has been successfully refreshed."),
                            "type": "success",
                            "sticky": False,
                        },
                    }
                else:
                    raise UserError(_(
                        "Could not find page %s in the list of accessible pages. "
                        "You may need to re-authenticate."
                    ) % self.page_name)

            else:
                raise UserError(_(
                    "Failed to refresh token. Response: %s. "
                    "You may need to re-authenticate by updating the account."
                ) % response)

        except Exception as e:
            print(f"ERROR: Error refreshing token: {str(e)}")
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": _("Token Refresh Failed"),
                    "message": _("Error: %s. Please try re-authenticating.") % str(e),
                    "type": "danger",
                    "sticky": True,
                },
            }

    def _action_post(self, message, image_ids=None, video_ids=None, link=None):
        """Feature #6: Enhanced Publishing - Multi-photo, video, and link support"""
        if self.media_type == "facebook" and self.page_access_token:
            base_params = {
                "access_token": self.page_access_token,
            }

            # Handle multiple images (requires multi-step process)
            if image_ids and len(image_ids) > 1:
                print(f"Publishing multi-photo post with {len(image_ids)} images")

                # Step 1: Upload all photos and collect their IDs
                photo_ids = []
                for image in image_ids:
                    upload_endpoint = f"{self.page_id}/photos"
                    upload_params = {
                        "published": "false",  # Upload unpublished
                        "access_token": self.page_access_token,
                    }

                    try:
                        files = {"source": base64.b64decode(image.datas)}
                        photo_response = self._request_facebook(
                            method="POST",
                            endpoint=upload_endpoint,
                            params=upload_params,
                            data=files,
                        )
                        if isinstance(photo_response, dict) and photo_response.get("id"):
                            photo_ids.append(photo_response["id"])
                            print(f"Uploaded photo ID: {photo_response['id']}")
                    except Exception as e:
                        print(f"ERROR: Error uploading photo: {str(e)}")
                        continue

                # Step 2: Create post with all photo IDs
                if photo_ids:
                    post_params = base_params.copy()
                    post_params["message"] = message

                    # Build attached_media parameter
                    attached_media = [{"media_fbid": photo_id} for photo_id in photo_ids]
                    post_params["attached_media"] = str(attached_media).replace("'", '"')

                    endpoint = f"{self.page_id}/feed"
                    response = self._request_facebook(
                        method="POST",
                        endpoint=endpoint,
                        params=post_params,
                    )

                    if isinstance(response, dict) and response.get("id"):
                        print(f"Multi-photo post created: {response['id']}")
                        return response.get("id")

            # Handle single image
            elif image_ids and len(image_ids) == 1:
                print("Publishing single photo post")
                endpoint = f"{self.page_id}/photos"
                params = base_params.copy()
                params["message"] = message

                try:
                    files = {"source": base64.b64decode(image_ids[0].datas)}
                    response = self._request_facebook(
                        method="POST",
                        endpoint=endpoint,
                        params=params,
                        data=files,
                    )
                    if isinstance(response, dict) and response.get("post_id"):
                        return response.get("post_id")
                except Exception as e:
                    print(f"ERROR: Error publishing photo: {str(e)}")

            # Handle video
            elif video_ids and len(video_ids) > 0:
                print("Publishing video post")
                endpoint = f"{self.page_id}/videos"
                params = base_params.copy()
                params["description"] = message

                try:
                    # Upload video file
                    video_data = base64.b64decode(video_ids[0].datas)
                    files = {"source": video_data}

                    response = self._request_facebook(
                        method="POST",
                        endpoint=endpoint,
                        params=params,
                        data=files,
                        timeout=60,  # Longer timeout for video uploads
                    )

                    if isinstance(response, dict) and response.get("id"):
                        print(f"Video post created: {response['id']}")
                        return response.get("id")
                except Exception as e:
                    print(f"ERROR: Error publishing video: {str(e)}")

            # Handle link post
            elif link:
                print("Publishing link post")
                endpoint = f"{self.page_id}/feed"
                params = base_params.copy()
                params["message"] = message
                params["link"] = link

                response = self._request_facebook(
                    method="POST",
                    endpoint=endpoint,
                    params=params,
                )

                if isinstance(response, dict) and response.get("id"):
                    print(f"Link post created: {response['id']}")
                    return response.get("id")

            # Handle text-only post
            else:
                print("Publishing text-only post")
                endpoint = f"{self.page_id}/feed"
                params = base_params.copy()
                params["message"] = message

                response = self._request_facebook(
                    method="POST",
                    endpoint=endpoint,
                    params=params,
                )

                if isinstance(response, dict) and response.get("id"):
                    print(f"Text post created: {response['id']}")
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

        print("=" * 80)
        print(f"===== DEBUG: action_sync_facebook_content - Manual sync started for account: {self.name}")

        try:
            # Sync posts
            self._sync_facebook_posts()
            # Sync reels
            self._sync_facebook_reels()
            # Sync ads (if configured)
            self._sync_facebook_ads()

            print("Manual sync completed successfully")
            print("=" * 80)

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
            print(f"ERROR: Error during manual sync: {str(e)}")
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

    def action_sync_with_date_range(self):
        """Open wizard to sync with custom date range"""
        self.ensure_one()
        return {
            "name": "Sync from Custom Date Range",
            "type": "ir.actions.act_window",
            "res_model": "wizard.facebook.sync",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_account_id": self.id,
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
        # Use the filtered sync method with no filters (incremental sync)
        self._sync_facebook_posts_filtered()

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
        # Use the filtered sync method with no filters (incremental sync)
        self._sync_facebook_reels_filtered()

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

        # Check if ad account is configured
        if not self.fb_ad_account_id:
            print(f"No ad account configured for page: {self.page_name}. Skipping ad sync.")
            self.last_ads_sync_at = fields.Datetime.now()
            return

        if not self.page_access_token:
            print(f"WARNING: No access token for account {self.name}")
            return

        print(f"Syncing ads for page: {self.page_name} (Ad Account: {self.fb_ad_account_id})")

        # Fetch ads from Marketing API
        ad_fields = "id,name,status,creative"
        params = {
            "access_token": self.page_access_token,
            "fields": ad_fields,
            "limit": 100,
        }

        # Incremental sync with filtering
        if self.last_ads_sync_at:
            params["filtering"] = json.dumps([{
                "field": "updated_time",
                "operator": "GREATER_THAN",
                "value": int(self.last_ads_sync_at.timestamp()),
            }])

        endpoint = f"{self.fb_ad_account_id}/ads"
        response = self._request_facebook(endpoint=endpoint, params=params)

        if isinstance(response, dict) and response.get("data"):
            ads_data = response.get("data", [])
            print(f"Retrieved {len(ads_data)} ads from Facebook")

            created_count = 0
            updated_count = 0

            for ad_data in ads_data:
                try:
                    fb_ad_id = ad_data.get("id")

                    # Fetch insights for this ad
                    insights_fields = (
                        "impressions,reach,clicks,ctr,spend,currency,"
                        "actions,cost_per_action_type"
                    )
                    insights_params = {
                        "access_token": self.page_access_token,
                        "fields": insights_fields,
                        "level": "ad",
                    }
                    insights_endpoint = f"{fb_ad_id}/insights"
                    insights_response = self._request_facebook(
                        endpoint=insights_endpoint, params=insights_params
                    )

                    if not isinstance(insights_response, dict):
                        print(f"WARNING: Failed to get insights for ad {fb_ad_id}")
                        continue

                    insights_data = insights_response.get("data", [{}])[0] if insights_response.get("data") else {}

                    # Parse actions for leads and conversions
                    actions = insights_data.get("actions", [])
                    leads_total = sum(
                        int(action.get("value", 0))
                        for action in actions
                        if action.get("action_type") == "lead"
                    )
                    conversions_total = sum(
                        int(action.get("value", 0))
                        for action in actions
                        if action.get("action_type") in ["offsite_conversion", "onsite_conversion"]
                    )

                    # Build metrics data
                    metrics_data = {
                        "message": ad_data.get("name", "") or f"Ad {fb_ad_id}",
                        "fb_content_id": fb_ad_id,
                        "fb_ad_id": fb_ad_id,
                        "fb_content_type": "ad",
                        "ad_name": ad_data.get("name"),
                        "impressions_total": int(insights_data.get("impressions", 0)),
                        "reach_unique": int(insights_data.get("reach", 0)),
                        "clicks_total": int(insights_data.get("clicks", 0)),
                        "ctr_pct": float(insights_data.get("ctr", 0)),
                        "spend_amount": float(insights_data.get("spend", 0)),
                        "currency": insights_data.get("currency", "USD"),
                        "leads_total": leads_total,
                        "conversions_total": conversions_total,
                        "account_ids": [(6, 0, [self.id])],  # Required field
                        "image_urls": "[]",  # Required by kanban template
                        "state": "published",  # Ads synced from Facebook are already published
                    }

                    # Deduplication
                    existing_post = self.env["social.post"].search(
                        [
                            "|",
                            ("fb_ad_id", "=", fb_ad_id),
                            ("fb_content_id", "=", fb_ad_id),
                        ],
                        limit=1,
                    )

                    if existing_post:
                        existing_post.write_metrics_snapshot(metrics_data)
                        updated_count += 1
                    else:
                        post = self.env["social.post"].create(metrics_data)
                        post.write_metrics_snapshot(metrics_data)
                        created_count += 1

                except Exception as e:
                    print(f"ERROR: Error processing ad {ad_data.get('id')}: {str(e)}")
                    continue

            print(f"Ads sync completed: {created_count} created, {updated_count} updated")
        else:
            print(f"WARNING: No ads data in response: {response}")

        self.last_ads_sync_at = fields.Datetime.now()

    def _sync_facebook_comments(self, from_datetime=None, to_datetime=None):
        """Feature #4: Sync comments from Facebook posts

        API Endpoints:
        - /{POST_ID}/comments - Get comments on a post
        - /{COMMENT_ID}/comments - Get replies to a comment
        """
        self.ensure_one()
        if not self.page_id or not self.page_access_token:
            print(f"WARNING: No page_id or access token for account {self.name}")
            return

        print(f"Syncing comments for page: {self.page_name}")

        # Get all Facebook posts for this account
        posts = self.env["social.post"].search([
            ("media_id.media_type", "=", "facebook"),
            ("fb_content_id", "!=", False),
        ])

        total_comments_synced = 0

        for post in posts:
            try:
                post_id = post.fb_content_id

                # Fetch comments for this post
                fields_str = "id,message,from,created_time,comment_count"
                params = {
                    "access_token": self.page_access_token,
                    "fields": fields_str,
                    "limit": 100,
                }

                # Add date filter if provided
                if from_datetime:
                    params["since"] = int(from_datetime.timestamp())

                endpoint = f"{post_id}/comments"
                response = self._request_facebook(endpoint=endpoint, params=params)

                if isinstance(response, dict) and response.get("data"):
                    comments_data = response.get("data", [])
                    print(f"Retrieved {len(comments_data)} comments for post {post_id}")

                    for comment_data in comments_data:
                        self._process_comment_data(comment_data, post.id)
                        total_comments_synced += 1

                        # Fetch replies if comment has replies
                        if comment_data.get("comment_count", 0) > 0:
                            self._sync_comment_replies(comment_data.get("id"), post.id)

            except Exception as e:
                print(f"ERROR: Error syncing comments for post {post.fb_content_id}: {str(e)}")
                continue

        print(f"Comments sync completed: {total_comments_synced} comments synced")

    def _sync_comment_replies(self, parent_comment_id, post_id):
        """Sync replies to a comment"""
        try:
            fields_str = "id,message,from,created_time"
            params = {
                "access_token": self.page_access_token,
                "fields": fields_str,
                "limit": 50,
            }

            endpoint = f"{parent_comment_id}/comments"
            response = self._request_facebook(endpoint=endpoint, params=params)

            if isinstance(response, dict) and response.get("data"):
                replies_data = response.get("data", [])

                # Find parent comment in Odoo
                parent_comment = self.env["social.comment"].search([
                    ("comment_id", "=", parent_comment_id)
                ], limit=1)

                for reply_data in replies_data:
                    self._process_comment_data(reply_data, post_id, parent_comment.id if parent_comment else False)

        except Exception as e:
            print(f"ERROR: Error syncing replies for comment {parent_comment_id}: {str(e)}")

    def _process_comment_data(self, comment_data, post_id, parent_id=False):
        """Process and store comment data"""
        comment_id = comment_data.get("id")

        # Check if comment already exists
        existing_comment = self.env["social.comment"].search([
            ("comment_id", "=", comment_id)
        ], limit=1)

        author_data = comment_data.get("from", {})

        comment_vals = {
            "post_id": post_id,
            "comment_id": comment_id,
            "parent_id": parent_id,
            "message": comment_data.get("message", ""),
            "author_name": author_data.get("name"),
            "author_id": author_data.get("id"),
            "created_time": self._parse_facebook_datetime(comment_data.get("created_time")),
            "last_sync_at": fields.Datetime.now(),
        }

        if existing_comment:
            existing_comment.write(comment_vals)
        else:
            self.env["social.comment"].create(comment_vals)

    def _reply_to_facebook_comment(self, comment_id, message):
        """Reply to a Facebook comment

        Args:
            comment_id: Facebook comment ID
            message: Reply message text

        Returns:
            dict: Response from Facebook API
        """
        self.ensure_one()
        if not self.page_access_token:
            return False

        params = {
            "message": message,
            "access_token": self.page_access_token,
        }

        endpoint = f"{comment_id}/comments"
        response = self._request_facebook(
            method="POST",
            endpoint=endpoint,
            params=params,
        )

        if isinstance(response, dict) and response.get("id"):
            print(f"Successfully replied to comment {comment_id}")
            return response
        else:
            print(f"ERROR: Failed to reply to comment {comment_id}: {response}")
            return False

    def _hide_facebook_comment(self, comment_id):
        """Hide a Facebook comment

        Args:
            comment_id: Facebook comment ID

        Returns:
            bool: True if successful
        """
        self.ensure_one()
        if not self.page_access_token:
            return False

        params = {
            "is_hidden": "true",
            "access_token": self.page_access_token,
        }

        endpoint = comment_id
        response = self._request_facebook(
            method="POST",
            endpoint=endpoint,
            params=params,
        )

        if isinstance(response, dict) and response.get("success"):
            print(f"Successfully hid comment {comment_id}")
            return True
        else:
            print(f"ERROR: Failed to hide comment {comment_id}: {response}")
            return False

    def _sync_facebook_leads(self, from_datetime=None, to_datetime=None):
        """Feature #5: Sync leads from Facebook Lead Forms

        This method syncs leads from all lead forms associated with this account.

        Args:
            from_datetime: Optional start datetime for filtering leads
            to_datetime: Optional end datetime for filtering leads

        API Endpoint:
        - /{FORM_ID}/leads?fields=id,created_time,field_data
        """
        self.ensure_one()
        if not self.page_id or not self.page_access_token:
            print(f"WARNING: No page_id or access token for account {self.name}")
            return

        print(f"Syncing leads for page: {self.page_name}")

        # Get all lead forms for this account
        lead_forms = self.env["social.lead.form"].search([
            ("account_id", "=", self.id)
        ])

        if not lead_forms:
            print(f"No lead forms configured for account {self.name}")
            return

        total_leads_synced = 0

        for lead_form in lead_forms:
            try:
                print(f"Syncing leads for form: {lead_form.name} (ID: {lead_form.fb_form_id})")

                # Build params
                params = {
                    "access_token": self.page_access_token,
                    "fields": "id,created_time,field_data",
                    "limit": 100,
                }

                # Add date filters if provided
                if from_datetime:
                    params["filtering"] = json.dumps([{
                        "field": "time_created",
                        "operator": "GREATER_THAN",
                        "value": int(from_datetime.timestamp()),
                    }])
                elif lead_form.last_sync_at:
                    # Incremental sync using last sync time
                    params["filtering"] = json.dumps([{
                        "field": "time_created",
                        "operator": "GREATER_THAN",
                        "value": int(lead_form.last_sync_at.timestamp()),
                    }])

                endpoint = f"{lead_form.fb_form_id}/leads"
                response = self._request_facebook(endpoint=endpoint, params=params)

                if isinstance(response, dict) and response.get("data"):
                    leads_data = response.get("data", [])
                    print(f"Retrieved {len(leads_data)} leads for form {lead_form.name}")

                    for lead_data in leads_data:
                        try:
                            lead_form._process_lead_data(lead_data)
                            total_leads_synced += 1
                        except Exception as e:
                            print(f"ERROR: Error processing lead {lead_data.get('id')}: {str(e)}")
                            continue

                    # Update last sync time for this form
                    lead_form.last_sync_at = fields.Datetime.now()
                else:
                    print(f"No new leads for form {lead_form.name}")

            except Exception as e:
                print(f"ERROR: Error syncing leads for form {lead_form.name}: {str(e)}")
                continue

        print(f"Leads sync completed: {total_leads_synced} leads synced")

    def _cron_sync_facebook_content(self, from_datetime=None, to_datetime=None, types=None):
        """Feature #9: Manual sync action with optional filters

        Args:
            from_datetime: Start datetime for sync (ISO format or datetime object)
            to_datetime: End datetime for sync (ISO format or datetime object)
            types: List of content types to sync ['posts', 'ads', 'reels', 'comments', 'leads']
                   If None, syncs all types

        Usage:
            # Sync all content for all accounts
            model._cron_sync_facebook_content()

            # Sync only posts and reels from last 7 days
            model._cron_sync_facebook_content(
                from_datetime='2025-01-01T00:00:00',
                types=['posts', 'reels']
            )
        """
        # Default to all sync types if not specified
        if types is None:
            types = ['posts', 'reels', 'ads']

        # Parse datetime strings if provided
        if from_datetime and isinstance(from_datetime, str):
            from_datetime = fields.Datetime.from_string(from_datetime)
        if to_datetime and isinstance(to_datetime, str):
            to_datetime = fields.Datetime.from_string(to_datetime)

        accounts = self.search([("media_type", "=", "facebook"), ("status", "=", "active")])
        print("=" * 80)
        print(f"Manual sync started for {len(accounts)} Facebook accounts")
        print(f"Parameters: from={from_datetime}, to={to_datetime}, types={types}")

        for account in accounts:
            try:
                print(f"Syncing account: {account.name} (ID: {account.id})")

                # Sync posts if requested
                if 'posts' in types:
                    print("  - Syncing posts...")
                    account._sync_facebook_posts_filtered(from_datetime, to_datetime)

                # Sync reels if requested
                if 'reels' in types:
                    print("  - Syncing reels...")
                    account._sync_facebook_reels_filtered(from_datetime, to_datetime)

                # Sync ads if requested
                if 'ads' in types:
                    print("  - Syncing ads...")
                    account._sync_facebook_ads()

                # Sync comments if requested (Feature #4: Comment Moderation System)
                if 'comments' in types:
                    print("  - Syncing comments...")
                    account._sync_facebook_comments(from_datetime, to_datetime)

                # Sync leads if requested (Feature #5: Lead Ads Integration)
                if 'leads' in types:
                    print("  - Syncing leads...")
                    account._sync_facebook_leads(from_datetime, to_datetime)

                print("  ✓ Account sync completed")

            except Exception as e:
                print(f"ERROR: Error syncing account {account.name}: {str(e)}")
                continue

        print("Manual sync completed for all accounts")
        print("=" * 80)

    def _sync_facebook_posts_filtered(self, from_datetime=None, to_datetime=None):
        """Sync posts with optional date filters"""
        print("=== DEBUG: _sync_facebook_posts_filtered called")
        self.ensure_one()
        if not self.page_id or not self.page_access_token:
            print(f"=== WARNING: No page_id or access token for account {self.name}")
            return

        print(f"=== Syncing posts for page: {self.page_name}")

        # Build params with date filters
        fields_str = (
            "id,message,created_time,permalink_url,"
            "attachments{media_type,media,url,subattachments{media{image}}},"
            "likes.summary(true),comments.summary(true),shares,"
            "insights.metric(post_impressions,post_impressions_unique,"
            "post_reactions_by_type_total,post_clicks)"
        )
        params = {
            "access_token": self.page_access_token,
            "fields": fields_str,
            "limit": 100,
        }

        # Add date filters if provided
        if from_datetime:
            params["since"] = int(from_datetime.timestamp())
        elif self.last_posts_sync_at:
            params["since"] = int(self.last_posts_sync_at.timestamp())

        if to_datetime:
            params["until"] = int(to_datetime.timestamp())

        # Call existing sync logic
        endpoint = f"{self.page_id}/posts"
        response = self._request_facebook(endpoint=endpoint, params=params)
        print("=== DEBUG: Facebook posts response received")
        print(f"=== DEBUG: Response: {response}")
        if isinstance(response, dict) and response.get("data"):
            self._process_posts_data(response.get("data", []))
            self.last_posts_sync_at = fields.Datetime.now()
        else:
            print(f"=== WARNING: No posts data in response: {response}")

    def _sync_facebook_reels_filtered(self, from_datetime=None, to_datetime=None):
        """Sync reels/videos with optional date filters"""
        self.ensure_one()
        if not self.page_id or not self.page_access_token:
            return

        print(f"=== Syncing reels for page: {self.page_name}")

        fields_str = (
            "id,title,description,created_time,permalink_url,shares,"
            "video_insights.metric(total_video_views,total_video_views_unique,"
            "total_video_view_time,total_video_complete_views,avg_time_watched)"
        )
        params = {
            "access_token": self.page_access_token,
            "fields": fields_str,
            "limit": 100,
        }

        # Add date filters if provided
        if from_datetime:
            params["since"] = int(from_datetime.timestamp())
        elif self.last_reels_sync_at:
            params["since"] = int(self.last_reels_sync_at.timestamp())

        if to_datetime:
            params["until"] = int(to_datetime.timestamp())

        endpoint = f"{self.page_id}/videos"
        response = self._request_facebook(endpoint=endpoint, params=params)

        if isinstance(response, dict) and response.get("data"):
            self._process_reels_data(response.get("data", []))
            self.last_reels_sync_at = fields.Datetime.now()
        else:
            print(f"=== WARNING: No videos data in response: {response}")

    def _parse_facebook_datetime(self, datetime_str):
        """Parse Facebook ISO 8601 datetime string to Python naive datetime

        Args:
            datetime_str: Facebook datetime string like '2025-10-17T07:43:52+0000'

        Returns:
            Naive datetime object (without timezone) or False if parsing fails
        """
        if not datetime_str:
            return False
        try:
            # Parse datetime with timezone, then convert to naive for Odoo
            # Facebook format: 2025-10-17T07:43:52+0000
            dt = dateutil_parser.parse(datetime_str)
            # Convert to naive datetime (remove timezone info) for Odoo
            return dt.replace(tzinfo=None)
        except:
            try:
                # Fallback: manual parsing (already naive)
                return datetime.strptime(datetime_str[:19], "%Y-%m-%dT%H:%M:%S")
            except:
                return False

    def _download_image_from_url(self, url, filename=None):
        """Download image from URL and create ir.attachment record

        Args:
            url: Image URL from Facebook
            filename: Optional filename for the attachment

        Returns:
            ir.attachment record or False if download fails
        """
        if not url:
            return False

        try:
            # Download image from URL
            response = requests.get(url, timeout=10)
            if response.status_code != 200:
                print(f"WARNING: Failed to download image from {url}, status: {response.status_code}")
                return False

            # Generate filename if not provided
            if not filename:
                # Extract filename from URL or generate one
                from urllib.parse import urlparse
                parsed_url = urlparse(url)
                filename = parsed_url.path.split('/')[-1] or f"facebook_image_{fields.Datetime.now().timestamp()}.jpg"

            # Create attachment
            attachment = self.env["ir.attachment"].create({
                "name": filename,
                "type": "binary",
                "datas": base64.b64encode(response.content),
                "mimetype": response.headers.get('content-type', 'image/jpeg'),
                "res_model": "social.post",
                # res_id will be set later when linking to post
            })

            print(f"Downloaded image: {filename} (ID: {attachment.id})")
            return attachment

        except Exception as e:
            print(f"ERROR: Failed to download image from {url}: {str(e)}")
            return False

    def _download_facebook_page_picture(self, page_id, access_token):
        """Download Facebook page profile picture

        Args:
            page_id: Facebook page ID
            access_token: Page or user access token

        Returns:
            base64 encoded image data or False if download fails
        """
        if not page_id or not access_token:
            return False

        try:
            # Get page picture URL from Facebook API
            # Request large picture (type=large gives ~200x200)
            params = {
                "access_token": access_token,
                "redirect": "false",  # Get JSON response with URL instead of redirect
                "type": "large",  # Options: small, normal, large, square
            }
            endpoint = f"{page_id}/picture"
            response = self._request_facebook(endpoint=endpoint, params=params)

            if isinstance(response, dict) and response.get("data", {}).get("url"):
                picture_url = response["data"]["url"]
                print(f"  Page picture URL: {picture_url[:80]}...")

                # Download the image
                img_response = requests.get(picture_url, timeout=10)
                if img_response.status_code == 200:
                    return base64.b64encode(img_response.content)
                else:
                    print(f"  WARNING: Failed to download page picture, status: {img_response.status_code}")
                    return False
            else:
                print(f"  WARNING: No picture URL in response: {response}")
                return False

        except Exception as e:
            print(f"  ERROR: Failed to download page picture: {str(e)}")
            return False

    def _process_posts_data(self, posts_data):
        """Extract post processing logic for reuse"""
        created_count = 0
        updated_count = 0

        for post_data in posts_data:
            try:
                fb_content_id = post_data.get("id")

                existing_post = self.env["social.post"].search(
                    [("fb_content_id", "=", fb_content_id)],
                    limit=1,
                )

                # Parse data - Extract images from attachments
                attachments = post_data.get("attachments", {}).get("data", [])
                media_url = None
                media_type_val = None
                image_attachments = []  # List to store downloaded image attachments

                if attachments:
                    first_attachment = attachments[0]
                    media_type_val = first_attachment.get("media_type")

                    # Handle album (multiple images)
                    if media_type_val == "album":
                        # Album contains multiple images in subattachments
                        subattachments = first_attachment.get("subattachments", {}).get("data", [])
                        for sub in subattachments:
                            if "media" in sub and "image" in sub["media"]:
                                img_url = sub["media"]["image"].get("src")
                                if img_url:
                                    # Download and create attachment
                                    attachment = self._download_image_from_url(img_url)
                                    if attachment:
                                        image_attachments.append(attachment.id)
                                    if not media_url:  # Store first image URL for preview
                                        media_url = img_url

                    # Handle single image
                    elif "media" in first_attachment:
                        if "image" in first_attachment["media"]:
                            media_url = first_attachment["media"]["image"].get("src")
                            if media_url:
                                # Download and create attachment
                                attachment = self._download_image_from_url(media_url)
                                if attachment:
                                    image_attachments.append(attachment.id)

                likes_count = post_data.get("likes", {}).get("summary", {}).get("total_count", 0)
                comments_count = post_data.get("comments", {}).get("summary", {}).get("total_count", 0)
                shares_count = post_data.get("shares", {}).get("count", 0)

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

                metrics_data = {
                    "message": post_data.get("message", "") or f"Post {fb_content_id}",
                    "fb_content_id": fb_content_id,
                    "fb_content_type": "post",
                    "permalink_url": post_data.get("permalink_url"),
                    "created_time": self._parse_facebook_datetime(post_data.get("created_time")),
                    "media_url": media_url,
                    "media_type": media_type_val,
                    "likes_count": likes_count,
                    "reactions_by_type_json": json.dumps(reactions_by_type) if reactions_by_type else "{}",
                    "comments_count": comments_count,
                    "shares_count": shares_count,
                    "impressions_total": impressions_total,
                    "reach_unique": reach_unique,
                    "clicks_total": clicks_total,
                    "account_ids": [(6, 0, [self.id])],  # Required field
                    "image_urls": "[]",  # Required by kanban template - empty array for now
                    "state": "published",  # Posts synced from Facebook are already published
                }

                # Add downloaded images to the post
                if image_attachments:
                    metrics_data["image_ids"] = [(6, 0, image_attachments)]

                if existing_post:
                    existing_post.write_metrics_snapshot(metrics_data)
                    updated_count += 1
                    # Ensure post_account record exists for dashboard
                    self._ensure_post_account_exists(existing_post, metrics_data, post_data)
                else:
                    post = self.env["social.post"].create(metrics_data)
                    post.write_metrics_snapshot(metrics_data)
                    created_count += 1
                    # Create post_account record for dashboard display
                    self._ensure_post_account_exists(post, metrics_data, post_data)

            except Exception as e:
                print(f"ERROR: Error processing post {post_data.get('id')}: {str(e)}")
                continue

        print(f"Posts processed: {created_count} created, {updated_count} updated")

    def _process_reels_data(self, videos_data):
        """Extract reel processing logic for reuse"""
        created_count = 0
        updated_count = 0

        for video_data in videos_data:
            try:
                fb_content_id = video_data.get("id")

                existing_post = self.env["social.post"].search(
                    [("fb_content_id", "=", fb_content_id)],
                    limit=1,
                )

                insights = video_data.get("video_insights", {}).get("data", [])
                plays_total = 0
                plays_unique = 0
                watch_time_sec = 0
                completed_views = 0

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

                shares_count = video_data.get("shares", {}).get("count", 0)

                metrics_data = {
                    "message": video_data.get("description", "") or video_data.get("title", "") or f"Video {fb_content_id}",
                    "fb_content_id": fb_content_id,
                    "fb_content_type": "reel",
                    "permalink_url": video_data.get("permalink_url"),
                    "created_time": self._parse_facebook_datetime(video_data.get("created_time")),
                    "media_type": "video",
                    "plays_total": plays_total,
                    "plays_unique": plays_unique,
                    "watch_time_sec": watch_time_sec,
                    "completed_views": completed_views,
                    "shares_count": shares_count,
                    "account_ids": [(6, 0, [self.id])],  # Required field
                    "image_urls": "[]",  # Required by kanban template
                    "state": "published",  # Reels synced from Facebook are already published
                }

                if existing_post:
                    existing_post.write_metrics_snapshot(metrics_data)
                    updated_count += 1
                    # Ensure post_account record exists for dashboard
                    self._ensure_post_account_exists(existing_post, metrics_data, video_data)
                else:
                    post = self.env["social.post"].create(metrics_data)
                    post.write_metrics_snapshot(metrics_data)
                    created_count += 1
                    # Create post_account record for dashboard display
                    self._ensure_post_account_exists(post, metrics_data, video_data)

            except Exception as e:
                print(f"ERROR: Error processing video {video_data.get('id')}: {str(e)}")
                continue

        print(f"Reels processed: {created_count} created, {updated_count} updated")

    def _ensure_post_account_exists(self, post, metrics_data, fb_data):
        """Ensure a social.post.account record exists for synced posts

        This allows synced posts to appear in the Dashboard view.

        Args:
            post: social.post record
            metrics_data: Dict with post metrics
            fb_data: Original Facebook API response data
        """
        # Check if post_account already exists for this account
        existing_post_account = self.env["social.post.account"].search([
            ("post_id", "=", post.id),
            ("account_id", "=", self.id),
        ], limit=1)

        if existing_post_account:
            # Update existing record with latest metrics
            existing_post_account.write({
                "message": metrics_data.get("message", ""),
                "published_date": metrics_data.get("created_time"),
                "comment_count": metrics_data.get("comments_count", 0),
                "like_count": metrics_data.get("likes_count", 0),
                "share_count": metrics_data.get("shares_count", 0),
                "view_count": metrics_data.get("plays_total", 0),  # For reels
                "post_account_url": metrics_data.get("permalink_url", ""),
            })
            print(f"  Updated post_account ID: {existing_post_account.id}")
        else:
            # Create new post_account record for dashboard
            # Convert image_ids from metrics_data format to Many2many format if present
            image_ids_value = []
            if "image_ids" in metrics_data and metrics_data["image_ids"]:
                image_ids_value = metrics_data["image_ids"]

            post_account_vals = {
                "post_id": post.id,
                "account_id": self.id,
                "media_id": self.media_id.id,
                "message": metrics_data.get("message", ""),
                "published_date": metrics_data.get("created_time"),
                "published": True,
                "state": "posted",
                "comment_count": metrics_data.get("comments_count", 0),
                "like_count": metrics_data.get("likes_count", 0),
                "share_count": metrics_data.get("shares_count", 0),
                "view_count": metrics_data.get("plays_total", 0),  # For reels
                "post_account_url": metrics_data.get("permalink_url", ""),
                "image_urls": metrics_data.get("image_urls", "[]"),
            }

            # Add images if available
            if image_ids_value:
                post_account_vals["image_ids"] = image_ids_value

            new_post_account = self.env["social.post.account"].create(post_account_vals)
            print(f"  Created post_account ID: {new_post_account.id} for Dashboard display")
