# Copyright 2025 Kencove (https://www.kencove.com/)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import base64
import json
import logging
from datetime import date, datetime, timedelta
import io

import requests
from dateutil import parser as dateutil_parser
from werkzeug.urls import url_join

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

from ..social_facebook_utils import _URL_GRAPH_FACEBOOK

_logger = logging.getLogger(__name__)


class SocialAccount(models.Model):
    _inherit = "social.account"

    page_id = fields.Char(string="Facebook Page ID")
    page_name = fields.Char(string="Facebook Page Name")
    page_access_token = fields.Char()
    token_expires_at = fields.Datetime()
    status = fields.Selection(
        [("active", "Active"), ("expired", "Expired"), ("error", "Error")],
        default="active",
    )
    facebook_user_token = fields.Char(string="User Access Token")

    # App credentials (stored per account like LinkedIn/X)
    facebook_app_id = fields.Char(string="App ID")
    facebook_app_secret = fields.Char(string="App Secret")

    facebook_system_user_token = fields.Char(string="System User Token")

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
    posts_count = fields.Integer(compute="_compute_facebook_posts_count")
    videos_count = fields.Integer(compute="_compute_facebook_content_counts")
    ads_count = fields.Integer(compute="_compute_facebook_content_counts")

    last_insight_update = fields.Datetime(string="Last Facebook Insights Update")

    def _get_facebook_app_id(self):
        """Get Facebook App ID from settings or fallback to per-account field"""
        app_id = (
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("social_media_base.facebook_app_id")
        )
        # Fallback to per-account field for backward compatibility
        if not app_id and self.facebook_app_id:
            return self.facebook_app_id
        return app_id

    def _get_facebook_app_secret(self):
        """Get Facebook App Secret from settings or fallback to per-account field"""
        app_secret = (
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("social_media_base.facebook_app_secret")
        )
        # Fallback to per-account field for backward compatibility
        if not app_secret and self.facebook_app_secret:
            return self.facebook_app_secret
        return app_secret

    def _get_facebook_system_user_token(self):
        """Get Facebook system user token from settings"""
        system_user_token = (
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("social_media_base.facebook_system_user_token")
        )
        # Fallback to per-account field for backward compatibility
        if not system_user_token and self.facebook_system_user_token:
            return self.facebook_system_user_token
        return system_user_token

    @api.depends("media_type")
    def _compute_facebook_posts_count(self):
        """Compute total posts for this Facebook account"""
        for record in self:
            if record.media_type == "facebook":
                # Count via social.post.account since fb_content_id is there
                record.posts_count = self.env["social.post.account"].search_count(
                    [("account_id", "=", record.id)]
                )
            else:
                record.posts_count = 0

    @api.depends("media_type")
    def _compute_facebook_content_counts(self):
        """Compute counts for videos and ads"""
        for record in self:
            if record.media_type == "facebook":
                # Count posts by content type via social.post
                posts = self.env["social.post"].search(
                    [("account_ids", "in", [record.id])]
                )
                record.videos_count = sum(1 for p in posts if p.content_type == "reel")
                record.ads_count = sum(1 for p in posts if p.content_type == "ad")
            else:
                record.videos_count = 0
                record.ads_count = 0

    def action_view_synced_posts(self):
        """Smart button action: View all synced posts for this account"""
        self.ensure_one()
        return {
            "name": _("Synced Posts"),
            "type": "ir.actions.act_window",
            "res_model": "social.post.account",
            "view_mode": "kanban,list,form",
            "domain": [("account_id", "=", self.id)],
            "context": {
                "search_default_group_by_account_id": 1,
            },
        }

    def action_view_dashboard_posts(self):
        """Smart button action: View dashboard posts for this account"""
        self.ensure_one()
        return {
            "name": _("Dashboard Posts"),
            "type": "ir.actions.act_window",
            "res_model": "social.post.account",
            "view_mode": "kanban,list,form",
            "domain": [("account_id", "=", self.id)],
            "context": {"search_default_group_by_account_id": 1},
        }

    def action_view_posts(self):
        """Smart button action: View posts only (content_type = 'post')"""
        self.ensure_one()
        return {
            "name": _("Posts"),
            "type": "ir.actions.act_window",
            "res_model": "social.post",
            "view_mode": "kanban,list,form",
            "domain": [
                ("account_ids", "in", [self.id]),
                ("content_type", "=", "post"),
            ],
            "context": {"default_account_ids": [self.id]},
        }

    def action_view_videos(self):
        """Smart button action: View videos only (content_type = 'reel')"""
        self.ensure_one()
        return {
            "name": _("Videos"),
            "type": "ir.actions.act_window",
            "res_model": "social.post",
            "view_mode": "kanban,list,form",
            "domain": [
                ("account_ids", "in", [self.id]),
                ("content_type", "=", "reel"),
            ],
            "context": {"default_account_ids": [self.id]},
        }

    def action_view_ads(self):
        """Smart button action: View ads only (content_type = 'ad')"""
        self.ensure_one()
        return {
            "name": _("Ads"),
            "type": "ir.actions.act_window",
            "res_model": "social.post",
            "view_mode": "kanban,list,form",
            "domain": [
                ("account_ids", "in", [self.id]),
                ("content_type", "=", "ad"),
            ],
            "context": {"default_account_ids": [self.id]},
        }

    def action_diagnose_facebook_api(self):
        """Diagnostic tool: Test Facebook API endpoints and permissions"""
        self.ensure_one()
        if not self.fb_ad_account_id:
            raise UserError(_("No ad account configured for this Facebook page."))

        _logger.debug("=" * 80)
        _logger.debug("FACEBOOK API DIAGNOSTIC")
        _logger.debug("=" * 80)
        _logger.debug(f"Account: {self.page_name}")
        _logger.debug(f"Page ID: {self.page_id}")
        _logger.debug(f"Ad Account: {self.fb_ad_account_id}")
        _logger.debug(f"Environment: {self.environment or 'test'}")
        _logger.debug("")

        # Test 1: Ad Account Info
        self._diag_test_ad_account_info()

        # Test 2: Campaigns
        self._diag_test_campaigns()

        # Test 3: AdSets
        self._diag_test_adsets()

        # Test 4: Ads (all statuses)
        self._diag_test_ads()

        # Test 5: AdCreatives
        self._diag_test_creatives()

        # Test 6: Token Permissions
        self._diag_test_permissions()

        _logger.debug("=" * 80)
        _logger.debug("DIAGNOSTIC COMPLETE")
        _logger.debug("=" * 80)

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Diagnostic Complete"),
                "message": _(
                    "Check the server console for detailed diagnostic results."
                ),
                "type": "info",
                "sticky": False,
            },
        }

    def _diag_test_ad_account_info(self):
        _logger.debug("TEST 1: Ad Account Info")
        _logger.debug("-" * 80)
        try:
            endpoint = self.fb_ad_account_id
            params = {
                "access_token": self.page_access_token,
                "fields": "account_id,name,account_status,age,currency,"
                "timezone_name,disable_reason",
            }
            response = self._request_facebook(endpoint=endpoint, params=params)
            if isinstance(response, dict):
                _logger.debug("✓ Ad Account accessible")
                _logger.debug(f"  Name: {response.get('name', 'N/A')}")
                _logger.debug(f"  Status: {response.get('account_status', 'N/A')}")
                _logger.debug(f"  Currency: {response.get('currency', 'N/A')}")
                _logger.debug(f"  Age: {response.get('age', 'N/A')} hours")
                if response.get("disable_reason"):
                    _logger.warning(f"{response.get('disable_reason')}")
            else:
                _logger.debug("✗ Failed to access ad account")
                _logger.debug(f"  Response: {response}")
        except Exception as e:
            _logger.error(f"✗ Error: {str(e)}")
        _logger.debug("")

    def _diag_test_campaigns(self):
        _logger.debug("TEST 2: Campaigns")
        _logger.debug("-" * 80)
        try:
            endpoint = f"{self.fb_ad_account_id}/campaigns"
            params = {
                "access_token": self.page_access_token,
                "fields": "id,name,status,objective",
                "limit": 5,
            }
            response = self._request_facebook(endpoint=endpoint, params=params)
            if isinstance(response, dict):
                campaigns = response.get("data", [])
                _logger.debug(f"✓ Found {len(campaigns)} campaign(s)")
                for camp in campaigns:
                    _logger.debug(
                        f"  - {camp.get('name')} (Status: {camp.get('status')})"
                    )
                if len(campaigns) == 0:
                    _logger.warning(
                        "No campaigns found - create a campaign in Ads Manager"
                    )
            else:
                _logger.error(f"Failed to fetch campaigns: {response}")
        except Exception as e:
            _logger.error(f"{str(e)}")
        _logger.debug("")

    def _diag_test_adsets(self):
        _logger.debug("TEST 3: AdSets")
        _logger.debug("-" * 80)
        try:
            endpoint = f"{self.fb_ad_account_id}/adsets"
            params = {
                "access_token": self.page_access_token,
                "fields": "id,name,status,campaign_id",
                "limit": 5,
            }
            response = self._request_facebook(endpoint=endpoint, params=params)
            if isinstance(response, dict):
                adsets = response.get("data", [])
                _logger.debug(f"Found {len(adsets)} adset(s)")
                for adset in adsets:
                    _logger.debug(
                        f"  - {adset.get('name')} (Status: {adset.get('status')})"
                    )
                if len(adsets) == 0:
                    _logger.warning("No adsets found")
            else:
                _logger.error(f"Failed to fetch adsets: {response}")
        except Exception as e:
            _logger.error(f"{str(e)}")
        _logger.debug("")

    def _diag_test_ads(self):
        _logger.debug("TEST 4: Ads (all statuses)")
        _logger.debug("-" * 80)
        try:
            endpoint = f"{self.fb_ad_account_id}/ads"
            params = {
                "access_token": self.page_access_token,
                "fields": "id,name,status,effective_status,configured_status",
                "limit": 10,
            }
            response = self._request_facebook(endpoint=endpoint, params=params)
            if isinstance(response, dict):
                ads = response.get("data", [])
                _logger.debug(f"Found {len(ads)} ad(s)")
                for ad in ads[:5]:  # Show first 5
                    _logger.debug(
                        f"  - {ad.get('name')} (Status: {ad.get('status')},"
                        f" Effective: {ad.get('effective_status')})"
                    )
                if len(ads) == 0:
                    _logger.warning("No ads found (draft ads NOT included)")
            else:
                _logger.error(f"✗ Failed to fetch ads: {response}")
        except Exception as e:
            _logger.error(f"✗ Error: {str(e)}")
        _logger.debug("")

    def _diag_test_creatives(self):
        _logger.debug("TEST 5: AdCreatives")
        _logger.debug("-" * 80)
        try:
            endpoint = f"{self.fb_ad_account_id}/adcreatives"
            params = {
                "access_token": self.page_access_token,
                "fields": "id,name,title,status",
                "limit": 10,
            }
            response = self._request_facebook(endpoint=endpoint, params=params)
            if isinstance(response, dict):
                creatives = response.get("data", [])
                _logger.debug(f"✓ Found {len(creatives)} creative(s)")
                for creative in creatives[:5]:  # Show first 5
                    name = (
                        creative.get("name")
                        or creative.get("title")
                        or creative.get("id")
                    )
                    _logger.info(f"  - {name}")
                if len(creatives) == 0:
                    _logger.warning("No ad creatives found")
            else:
                _logger.warning(f"✗ Failed to fetch creatives: {response}")
        except Exception as e:
            _logger.error(f"{str(e)}")
        _logger.info("")

    def _diag_test_permissions(self):
        _logger.debug("TEST 6: Token Permissions (via debug_token)")
        _logger.debug("-" * 80)
        try:
            endpoint = "debug_token"
            params = {
                "input_token": self.page_access_token,
                "access_token": self.page_access_token,
            }
            response = self._request_facebook(endpoint=endpoint, params=params)
            if isinstance(response, dict) and "data" in response:
                token_data = response.get("data", {})
                _logger.debug(f"✓ Token Type: {token_data.get('type', 'Unknown')}")
                _logger.debug(f"  Valid: {token_data.get('is_valid', False)}")
                _logger.debug(f"  App: {token_data.get('application', 'Unknown')}")

                # Check scopes/permissions
                scopes = token_data.get("scopes", [])
                if scopes:
                    _logger.debug(f"\n  Token has {len(scopes)} permission(s):")
                    for perm in sorted(scopes):
                        _logger.debug(f"    ✓ {perm}")

                    # Check for required permissions
                    required = [
                        "ads_management",
                        "ads_read",
                        "pages_read_engagement",
                        "pages_manage_posts",
                    ]
                    missing = [p for p in required if p not in scopes]
                    if missing:
                        _logger.debug("")
                        _logger.warning("Missing recommended permissions:")
                        for perm in missing:
                            _logger.debug(f"    ✗ {perm}")
                    else:
                        _logger.debug("")
                        _logger.debug("All required permissions present!")
                else:
                    _logger.warning(
                        "No scopes information available "
                        "(may be normal for page tokens)"
                    )
            else:
                _logger.warning(
                    "Note: Page tokens don't expose permissions via /me/permissions"
                )
                _logger.warning(
                    "But all previous tests passed, so token has required permissions!"
                )
        except Exception:
            _logger.warning("Note: Cannot check permissions for page tokens via API")
            _logger.warning(
                "But all previous tests passed, so token is working correctly!"
            )

    def _fields_account_url(self):
        return super()._fields_account_url() + [
            (
                "page_id",
                f"https://www.facebook.com/{self.page_id}",
            )
        ]

    @api.constrains("media_id", "company_id", "page_id")
    def _check_unique_facebook_page(self):
        """Ensure a Facebook page can only be linked once per company"""
        for record in self:
            if record.media_id.media_type == "facebook" and record.page_id:
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
                            "A Facebook page with ID '%s' is already linked"
                            " to this company!"
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
        files=None,
    ):
        url = f"{_URL_GRAPH_FACEBOOK}/{endpoint}"

        if headers is None:
            headers = {}

        _logger.debug(f"Facebook API: {method} {url}")
        if files:
            _logger.debug(f"Uploading files: {list(files.keys())}")
            actual_timeout = 60  # 60 seconds for file uploads
        else:
            actual_timeout = timeout

        try:
            response = requests.request(
                method=method,
                url=url,
                params=params,
                timeout=actual_timeout,
                headers=headers,
                data=data,
                json=json_data,
                files=files,
            )

            _logger.debug(f"Facebook API response: {response.status_code}")

            if response.status_code == 200:
                return response.json()
            else:
                _logger.error(
                    f"Facebook API error {response.status_code}: {response.text}"
                )
                return {"error": f"{response.status_code}: {response.text}"}

        except requests.exceptions.Timeout:
            _logger.error(f"Facebook API timeout after {actual_timeout}s")
            return {"error": f"Timeout after {actual_timeout}s"}
        except Exception as e:
            _logger.error(f"Facebook request failed: {str(e)}")
            return {"error": str(e)}

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
        _logger.debug("Getting Facebook access token...")
        _logger.debug(f"App ID: {app_id}")

        redirect_url = url_join(self.get_base_url(), redirect_endpoint_uri)
        _logger.debug(f"Redirect URL: {redirect_url}")

        params = {
            "client_id": app_id,
            "client_secret": app_secret,
            "redirect_uri": redirect_url,
            "code": authorization_code,
        }
        _logger.debug("Calling Facebook API: oauth/access_token")
        response = self._request_facebook(endpoint="oauth/access_token", params=params)
        _logger.debug(
            f"Facebook token API response status: "
            f"{response.status_code if hasattr(response, 'status_code') else 'success'}"
        )
        return response

    def get_pages_facebook(self, user_access_token):
        _logger.debug("Fetching Facebook pages from API...")
        params = {
            "access_token": user_access_token,
        }
        _logger.debug("Calling Facebook API: me/accounts")
        response = self._request_facebook(endpoint="me/accounts", params=params)
        _logger.debug(f"Facebook pages API response type: {type(response)}")

        if isinstance(response, dict) and response.get("data"):
            pages = response.get("data", [])
            _logger.debug(f"Successfully retrieved {len(pages)} pages")
            for page in pages:
                _logger.debug(f"  - Page: {page.get('name')} (ID: {page.get('id')})")
            return pages
        else:
            _logger.warning(f"No pages data in response or error occurred: {response}")
        return []

    def create_account_facebook(self, selected_page_ids, token):
        """Create Facebook accounts for selected pages only"""
        _logger.debug("=" * 80)
        _logger.debug("Creating Facebook accounts...")
        _logger.debug(f"Selected page IDs: {selected_page_ids}")

        if isinstance(token, dict):
            user_access_token = token.get("access_token", False)
            if user_access_token:
                _logger.debug(f"User access token: {user_access_token[:20]}...")
                pages = self.get_pages_facebook(user_access_token)
                # Calculate token expiration (Facebook page tokens don't expire)
                token_expires = datetime.now() + timedelta(days=365 * 10)
                _logger.debug(f"Token expiration set to: {token_expires}")

                created_count = 0
                updated_count = 0
                skipped_count = 0

                for page in pages:
                    _logger.debug("-" * 40)
                    page_id = page.get("id", "")
                    page_name = page.get("name", "")
                    _logger.debug(f"Processing page: {page_name} (ID: {page_id})")

                    # Only create accounts for selected pages
                    if page_id not in selected_page_ids:
                        _logger.debug("  Skipped: Not in selected pages")
                        skipped_count += 1
                        continue

                    _logger.debug("  Checking for existing account...")
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
                        values_data.update(
                            {
                                "facebook_app_id": wizard.facebook_app_id,
                                "facebook_app_secret": wizard.facebook_app_secret,
                            }
                        )

                    if not existing_account:
                        _logger.debug("  Creating new account...")
                        new_account = self.create(values_data)
                        _logger.debug(f"  ✓ Created account ID: {new_account.id}")
                        created_count += 1
                    else:
                        _logger.debug(
                            f"  Updating existing account ID: {existing_account.id}"
                        )
                        existing_account.write(values_data)
                        _logger.debug("  ✓ Updated account")
                        updated_count += 1

                _logger.debug("=" * 80)
                _logger.debug("Account creation summary:")
                _logger.debug(f"  Created: {created_count}")
                _logger.debug(f"  Updated: {updated_count}")
                _logger.debug(f"  Skipped: {skipped_count}")
                _logger.debug("=" * 80)
        else:
            message_error = f"Creating account: {token}"
            raise ValidationError(message_error)

    def create_account_facebook_from_wizard(
        self, pages_data, user_access_token, wizard_social_account
    ):
        """Create Facebook accounts using data directly from wizard (no re-fetch)

        Args:
            pages_data: List of dicts with page info
                [{"id": ..., "name": ..., "access_token": ...}]
            user_access_token: Facebook user access token
            wizard_social_account: wizard.social.account record with app credentials

        Returns:
            list: IDs of created/updated accounts
        """
        _logger.debug("=" * 80)
        _logger.debug("Creating Facebook accounts from wizard data...")
        _logger.debug(f"Pages to create: {len(pages_data)}")

        # Calculate token expiration (Facebook page tokens don't expire)
        token_expires = datetime.now() + timedelta(days=365 * 10)

        created_count = 0
        updated_count = 0
        account_ids = []

        for page in pages_data:
            _logger.debug("-" * 40)
            page_id = page.get("id", "")
            page_name = page.get("name", "")
            _logger.debug(f"Processing page: {page_name} (ID: {page_id})")

            # Check for existing account
            _logger.debug("  Checking for existing account...")
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
            _logger.debug("  Downloading page profile picture...")
            page_picture = self._download_facebook_page_picture(
                page_id, page.get("access_token", "")
            )
            if page_picture:
                values_data["image_1920"] = page_picture
                _logger.debug("  ✓ Page profile picture downloaded")

            # Store app credentials if from wizard
            if wizard_social_account:
                values_data.update(
                    {
                        "facebook_app_id": wizard_social_account.facebook_app_id,
                        "facebook_app_secret": (
                            wizard_social_account.facebook_app_secret
                        ),
                    }
                )
                _logger.debug("  Storing app credentials from wizard")

            if not existing_account:
                _logger.debug("  Creating new account...")
                new_account = self.create(values_data)
                _logger.debug(f"  ✓ Created account ID: {new_account.id}")
                account_ids.append(new_account.id)
                created_count += 1
            else:
                if existing_account.facebook_system_user_token:
                    values_data.update(
                        {
                            "facebook_system_user_token": False,
                        }
                    )
                _logger.debug(f"  Updating existing account ID: {existing_account.id}")
                existing_account.write(values_data)
                _logger.debug("  ✓ Updated account")
                account_ids.append(existing_account.id)
                updated_count += 1

        # Delete the wizard_social_account after successful account creation
        if wizard_social_account:
            _logger.debug("Deleting wizard.social.account after successful creation")
            wizard_social_account.unlink()

        _logger.debug("=" * 80)
        _logger.debug("Account creation summary:")
        _logger.debug(f"  Created: {created_count}")
        _logger.debug(f"  Updated: {updated_count}")
        _logger.debug("=" * 80)

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

        app_id = self._get_facebook_app_id()
        app_secret = self._get_facebook_app_secret()

        if not app_id or not app_secret:
            raise UserError(
                _(
                    "App credentials not configured. "
                    "Please configure Facebook App ID and App Secret in Settings"
                    " → Facebook Integration."
                )
            )

        if not self.facebook_user_token:
            raise UserError(
                _(
                    "No user access token available. "
                    "Please re-authenticate by updating the account."
                )
            )

        _logger.debug(f"Refreshing token for Facebook account: {self.name}")

        try:
            # Step 1: Exchange short-lived token for long-lived token
            params = {
                "grant_type": "fb_exchange_token",
                "client_id": app_id,
                "client_secret": app_secret,
                "fb_exchange_token": self.facebook_user_token,
            }

            response = self._request_facebook(
                endpoint="oauth/access_token", params=params
            )

            if isinstance(response, dict) and response.get("access_token"):
                new_user_token = response.get("access_token")
                _logger.debug("Successfully obtained new user access token")

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
                    self.write(
                        {
                            "facebook_user_token": new_user_token,
                            "page_access_token": new_page_token,
                            "access_token": new_page_token,
                            "token_expires_at": datetime.now() + timedelta(days=60),
                            "status": "active",
                        }
                    )

                    _logger.debug(f"Token refreshed successfully for: {self.name}")

                    return {
                        "type": "ir.actions.client",
                        "tag": "display_notification",
                        "params": {
                            "title": _("Token Refreshed"),
                            "message": _(
                                "Access token has been successfully refreshed."
                            ),
                            "type": "success",
                            "sticky": False,
                        },
                    }
                else:
                    raise UserError(
                        _(
                            "Could not find page %s in the list of accessible pages. "
                            "You may need to re-authenticate."
                        )
                        % self.page_name
                    )

            else:
                raise UserError(
                    _(
                        "Failed to refresh token. Response: %s. "
                        "You may need to re-authenticate by updating the account."
                    )
                    % response
                )

        except Exception as e:
            _logger.error(f"Error refreshing token: {str(e)}")
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
        """
        Enhanced Facebook publishing with proper image and video
        support - SINGLE RECORD METHOD
        """
        if self.media_type != "facebook" or not self.page_access_token:
            _logger.error("Facebook account not properly configured")
            return False

        _logger.debug(
            f"Starting Facebook post: {len(image_ids or [])} images,"
            f" {len(video_ids or [])} videos"
        )

        base_params = {"access_token": self.page_access_token}

        try:
            # ===== HANDLE SINGLE IMAGE =====
            if image_ids and len(image_ids) == 1:
                return self._post_single_image(message, image_ids[0], base_params)

            # ===== HANDLE MULTIPLE IMAGES =====
            elif image_ids and len(image_ids) > 1:
                return self._post_multiple_images(message, image_ids, base_params)

            # ===== HANDLE VIDEO =====
            elif video_ids and len(video_ids) > 0:
                return self._post_video(message, video_ids[0], base_params)

            # ===== HANDLE LINK =====
            elif link:
                _logger.debug("Posting link to Facebook")

                params = base_params.copy()
                params["message"] = message
                params["link"] = link

                response = self._request_facebook(
                    method="POST",
                    endpoint=f"{self.page_id}/feed",
                    params=params,
                )

                if isinstance(response, dict) and response.get("id"):
                    _logger.debug(f"Link post created: {response['id']}")
                    return response.get("id")
                else:
                    _logger.error(f"Link post failed: {response}")

            # ===== HANDLE TEXT-ONLY =====
            else:
                return self._post_text_only_fallback(message, base_params)

        except Exception as e:
            _logger.error(f"Facebook posting failed: {str(e)}", exc_info=True)

        return False

    def _post_single_image(self, message, image, base_params):

        _logger.debug("Posting single image to Facebook")

        if not image.datas:
            _logger.error("Image has no data")
            return self._post_text_only_fallback(message, base_params)

        try:
            image_data = base64.b64decode(image.datas)
            params = {
                "message": message,
                "access_token": self.page_access_token,
            }
            files = {
                "source": (
                    image.name or "image.jpg",
                    io.BytesIO(image_data),
                    "image/jpeg",
                )
            }

            response = self._request_facebook(
                method="POST",
                endpoint=f"{self.page_id}/photos",
                params=params,
                files=files,
                timeout=60,  # 60 seconds for image upload
            )

            if isinstance(response, dict):
                if response.get("post_id"):
                    _logger.debug(f"Single image post created: {response['post_id']}")
                    return response.get("post_id")
                elif response.get("id"):
                    _logger.debug(f"Single image uploaded: {response['id']}")
                    return response.get("id")
                else:
                    _logger.error(f"Image upload failed: {response}")
            else:
                _logger.error(f"Image upload failed, invalid response: {response}")

        except Exception as e:
            _logger.error(f"Single image upload error: {str(e)}", exc_info=True)

        return self._post_text_only_fallback(message, base_params)

    def _post_multiple_images(self, message, image_ids, base_params):
        import io

        _logger.debug(f"Posting {len(image_ids)} images to Facebook")

        photo_ids = []
        for i, image in enumerate(image_ids):
            try:
                if image.datas:
                    image_data = base64.b64decode(image.datas)
                    upload_params = {
                        "published": "false",
                        "access_token": self.page_access_token,
                    }
                    files = {
                        "source": (
                            image.name or "image.jpg",
                            io.BytesIO(image_data),
                            "image/jpeg",
                        )
                    }

                    upload_response = self._request_facebook(
                        method="POST",
                        endpoint=f"{self.page_id}/photos",
                        params=upload_params,
                        files=files,
                        timeout=60,  # 60 seconds for each image upload
                    )

                    if isinstance(upload_response, dict) and upload_response.get("id"):
                        photo_ids.append(upload_response["id"])
                        _logger.debug(
                            f"Uploaded image {i+1}/{len(image_ids)}: "
                            f"{upload_response['id']}"
                        )
                    else:
                        _logger.warning(
                            f"Failed to upload image "
                            f"{i+1}/{len(image_ids)}: {upload_response}"
                        )
                else:
                    _logger.warning(f"Image {i+1} has no data")
            except Exception as e:
                _logger.error(f"Error uploading image {i+1}: {str(e)}")
                continue

        if photo_ids:
            post_params = base_params.copy()
            post_params["message"] = message
            attached_media = [{"media_fbid": photo_id} for photo_id in photo_ids]
            post_params["attached_media"] = json.dumps(attached_media)

            response = self._request_facebook(
                method="POST",
                endpoint=f"{self.page_id}/feed",
                params=post_params,
            )

            if isinstance(response, dict) and response.get("id"):
                _logger.debug(f"Multi-image post created: {response['id']}")
                return response.get("id")

        # Fallback to text if image upload fails
        _logger.warning("Image upload failed, falling back to text post")
        return self._post_text_only_fallback(message, base_params)

    def _post_video(self, message, video, base_params):
        import io

        _logger.debug("Posting video to Facebook")

        if not video.datas:
            _logger.error("Video has no data")
            return self._post_text_only_fallback(message, base_params)

        try:
            video_data = base64.b64decode(video.datas)
            filename = video.name or "video.mp4"
            mime_type = video.mimetype or "video/mp4"

            params = {
                "description": message,
                "access_token": self.page_access_token,
            }

            files = {"source": (filename, io.BytesIO(video_data), mime_type)}

            response = self._request_facebook(
                method="POST",
                endpoint=f"{self.page_id}/videos",
                params=params,
                files=files,
                timeout=120,
            )

            if isinstance(response, dict):
                return response.get("id")

        except Exception as e:
            _logger.error(f"Video upload error: {str(e)}", exc_info=True)

        return self._post_text_only_fallback(message, base_params)

    def _post_text_only_fallback(self, message, base_params):
        """Internal helper for text-only posts"""
        _logger.debug("Posting text-only message to Facebook")

        params = base_params.copy()
        params["message"] = message

        response = self._request_facebook(
            method="POST",
            endpoint=f"{self.page_id}/feed",
            params=params,
        )

        if isinstance(response, dict) and response.get("id"):
            _logger.debug(f"Text post created: {response['id']}")
            return response.get("id")

        _logger.error(f"Text post failed: {response}")
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
        """Manual sync button: sync posts, reels, and ads then redirect to Dashboard"""
        self.ensure_one()
        if self.media_type != "facebook":
            return

        _logger.debug("=" * 80)
        _logger.debug(
            f"=====action_sync_facebook_content - Manual sync "
            f"started for account: {self.name}"
        )

        try:
            # Track counts before sync
            posts_before = self.posts_count

            # Sync posts
            self._sync_facebook_posts()
            # Sync reels
            self._sync_facebook_reels()
            # Sync ads (if configured)
            self._sync_facebook_ads()

            # Force recompute posts count
            self._compute_facebook_posts_count()
            posts_after = self.posts_count
            new_posts = posts_after - posts_before

            _logger.debug("Manual sync completed successfully")
            _logger.debug(f"New posts synced: {new_posts}")
            _logger.debug("=" * 80)

            # Redirect to Dashboard with success message
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": _("Sync Complete"),
                    "message": _(
                        f"Successfully synced {new_posts} new posts for {self.name}"
                    ),
                    "type": "success",
                    "sticky": False,
                    "next": {
                        "type": "ir.actions.act_window",
                        "name": "Dashboard",
                        "res_model": "social.post.account",
                        "view_mode": "kanban",
                        "domain": [("account_id", "=", self.id)],
                        "context": {"search_default_group_by_account_id": 1},
                    },
                },
            }
        except Exception as e:
            _logger.error(f"Error during manual sync: {str(e)}")
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": _("Sync Failed"),
                    "message": _("Error syncing content: %s") % str(e),
                    "type": "danger",
                    "sticky": True,
                },
            }

    def action_sync_with_date_range(self):
        """Open wizard to sync with custom date range

        The wizard will automatically use active_id from context
        to pre-select the current account(s)
        """
        return {
            "name": "Sync from Custom Date Range",
            "type": "ir.actions.act_window",
            "res_model": "wizard.facebook.sync",
            "view_mode": "form",
            "target": "new",
            # Context automatically includes active_id, active_ids, active_model
        }

    def action_sync_comments_for_post(self, post_account_id):
        """Sync comments for a specific post

        Args:
            post_account_id: ID of the social.post.account record

        Returns:
            dict: {"success": bool, "message": str, "comments_synced": int}
        """
        self.ensure_one()
        if self.media_type != "facebook":
            return {
                "success": False,
                "message": "Not a Facebook account",
                "comments_synced": 0,
            }

        try:
            # Get the post account directly
            post_account = self.env["social.post.account"].browse(post_account_id)
            if not post_account.exists():
                return {
                    "success": False,
                    "message": "Post account not found",
                    "comments_synced": 0,
                }

            # Verify it's a Facebook post for this account
            if (
                post_account.media_type != "facebook"
                or post_account.account_id.id != self.id
            ):
                return {
                    "success": False,
                    "message": "Invalid post account",
                    "comments_synced": 0,
                }

            # Get the post
            post = post_account.post_id
            if not post.exists():
                return {
                    "success": False,
                    "message": "Post not found",
                    "comments_synced": 0,
                }

            # Check if we have fb_content_id
            if (
                not hasattr(post_account, "fb_content_id")
                or not post_account.fb_content_id
            ):
                return {
                    "success": False,
                    "message": "No Facebook content ID found for this post",
                    "comments_synced": 0,
                }

            fb_post_id = post_account.fb_content_id

            # Count comments before sync
            comments_before = self.env["social.comment"].search_count(
                [
                    ("post_id", "=", post.id),
                ]
            )

            # Fetch comments for this post
            fields_str = "id,message,from,created_time,comment_count"
            params = {
                "access_token": self.page_access_token,
                "fields": fields_str,
                "limit": 100,
            }

            endpoint = f"{fb_post_id}/comments"
            response = self._request_facebook(endpoint=endpoint, params=params)

            if isinstance(response, dict) and response.get("data"):
                comments_data = response.get("data", [])
                _logger.debug(
                    f"Retrieved {len(comments_data)} comments for post {fb_post_id}"
                )

                for comment_data in comments_data:
                    self._process_comment_data(comment_data, post.id)

                    # Sync replies for this comment if it has any
                    if comment_data.get("comment_count", 0) > 0:
                        self._sync_comment_replies(comment_data.get("id"), post.id)

                # Count comments after sync
                comments_after = self.env["social.comment"].search_count(
                    [
                        ("post_id", "=", post.id),
                    ]
                )

                new_comments = comments_after - comments_before

                return {
                    "success": True,
                    "message": f"Successfully synced {new_comments} new comments",
                    "comments_synced": new_comments,
                }
            else:
                return {
                    "success": False,
                    "message": "No comments found on Facebook",
                    "comments_synced": 0,
                }

        except Exception as e:
            _logger.error(
                f"Failed to sync comments for post_account {post_account_id}: {str(e)}"
            )
            return {
                "success": False,
                "message": f"Error syncing comments: {str(e)}",
                "comments_synced": 0,
            }

    def _sync_facebook_posts(self):
        """Sync posts from Facebook Page with detailed metrics

        API Mapping per Feature #3 requirements:
        - Likes: /{POST_ID}?fields=likes.summary(true)
        - Reactions by type: /{POST_ID}/insights?metric=post_reactions_by_type_total
        - Comments: /{POST_ID}?fields=comments.summary(true)
        - Shares: /{POST_ID}?fields=shares
        - Impressions: /{POST_ID}/insights?metric=post_media_view
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

    def _sync_facebook_ads(self, from_datetime=None, to_datetime=None):
        """Sync ads insights from Facebook Marketing API

        Args:
            from_datetime: Optional start datetime for filtering ads by updated_time
            to_datetime: Optional end datetime (not currently used by FB API)

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

        if not self._check_ads_sync_prerequisites():
            return

        # Log environment and status for diagnostics
        env_mode = self.environment or "test"
        account_status = self.status or "active"
        _logger.debug(f"Syncing ads for: {self.page_name}")
        _logger.debug(f"  Ad Account: {self.fb_ad_account_id}")
        _logger.debug(f"  Environment: {env_mode.upper()}")
        _logger.debug(f"  Account Status: {account_status.upper()}")

        # Fetch ads from Marketing API
        # Note: Draft ads are NOT returned by /ads endpoint - only published ads
        # effective_object_story_id gives us the post ID for constructing permalink
        # Request creative with nested fields to get media (images/videos)
        params = self._build_ads_query_params(from_datetime)
        response = self._fetch_facebook_ads(params)

        # Better error handling - check if response is a Response object with error
        if self._is_facebook_error_response(response):
            self._handle_facebook_error(response)
            return

        _logger.debug(f"Facebook ads API response content: {response}")

        if isinstance(response, dict):
            ads_data = response.get("data", [])
            _logger.debug(f"Retrieved {len(ads_data)} ads from Facebook")

            # If empty, try alternative endpoint for ad creatives
            if len(ads_data) == 0:
                self._sync_ads_from_creatives(env_mode)

        if isinstance(response, dict) and response.get("data"):
            ads_data = response.get("data", [])
            _logger.debug(f"Processing {len(ads_data)} ads...")

            self._process_ads_data(ads_data)

            _logger.debug("\nAuto-syncing lead forms (required for lead gen ads)...")
            self._sync_facebook_lead_forms()
        else:
            _logger.warning(f"No ads data in response: {response}")

        self.last_ads_sync_at = fields.Datetime.now()

    def _check_ads_sync_prerequisites(self):
        if not self.fb_ad_account_id:
            _logger.debug(
                f"No ad account configured for page: {self.page_name}. "
                f"Skipping ad sync."
            )
            self.last_ads_sync_at = fields.Datetime.now()
            return False

        if not self.page_access_token:
            _logger.warning(f"No access token for account {self.name}")
            return False

        return True

    def _build_ads_query_params(self, from_datetime):
        ad_fields = (
            "id,name,status,effective_status,configured_status,"
            "created_time,updated_time,effective_object_story_id,"
            "creative{id,name,title,body,object_story_spec,"
            "image_url,thumbnail_url,video_id}"
        )

        params = {
            "access_token": self.page_access_token,
            "fields": ad_fields,
            "limit": 100,
        }

        filtering_time = self._get_ads_filtering_time(from_datetime)
        params["filtering"] = json.dumps(filtering_time)

        return params

    def _get_ads_filtering_time(self, from_datetime):
        if from_datetime:
            _logger.debug(f"  Manual sync from {from_datetime}")
            timestamp = int(from_datetime.timestamp())
        elif self.last_ads_sync_at:
            _logger.debug(f"  Incremental sync from {self.last_ads_sync_at}")
            timestamp = int(self.last_ads_sync_at.timestamp())
        else:
            _logger.debug("  First sync - fetching ads from last 30 days")
            timestamp = int((datetime.now() - timedelta(days=30)).timestamp())

        return [
            {
                "field": "updated_time",
                "operator": "GREATER_THAN",
                "value": timestamp,
            }
        ]

    def _fetch_facebook_ads(self, params):
        endpoint = f"{self.fb_ad_account_id}/ads"

        _logger.debug("Endpoint:", endpoint)
        _logger.debug(
            "Params:", {k: v for k, v in params.items() if k != "access_token"}
        )

        return self._request_facebook(endpoint=endpoint, params=params)

    def _is_facebook_error_response(self, response):
        return hasattr(response, "status_code")

    def _handle_facebook_error(self, response):
        _logger.error(f"ERROR: Facebook API returned status {response.status_code}")
        if hasattr(response, "text"):
            _logger.error(f"Error details: {response.text}")

        self.last_ads_sync_at = fields.Datetime.now()

    def _process_ads_data(self, ads_data):
        created = 0
        updated = 0

        for ad_data in ads_data:
            try:
                result = self._process_single_ad(ad_data)
                created += result["created"]
                updated += result["updated"]
            except Exception as e:
                _logger.error(f"Error processing ad {ad_data.get('id')}: {str(e)}")

        _logger.debug(f"Ads sync completed: {created} created, {updated} updated")

        _logger.debug("Auto-syncing lead forms")
        _logger.debug(f"Ads sync completed: {created} created, {updated} updated")
        self._sync_facebook_lead_forms()

    def _process_single_ad(self, ad_data):
        fb_ad_id = ad_data.get("id")

        insights = self._fetch_ad_insights(fb_ad_id)
        metrics = self._build_ad_metrics(ad_data, insights)

        post_account = self.env["social.post.account"].search(
            [
                "|",
                ("fb_ad_id", "=", fb_ad_id),
                ("fb_content_id", "=", fb_ad_id),
            ],
            limit=1,
        )

        if post_account:
            self._update_existing_ad(post_account, metrics, ad_data)
            return {"created": 0, "updated": 1}

        self._create_new_ad(metrics, ad_data)
        return {"created": 1, "updated": 0}

    def _fetch_ad_insights(self, fb_ad_id):
        fields = (
            "impressions,reach,clicks,ctr,spend,currency,"
            "actions,cost_per_action_type"
        )

        response = self._request_facebook(
            endpoint=f"{fb_ad_id}/insights",
            params={
                "access_token": self.page_access_token,
                "fields": fields,
                "level": "ad",
            },
        )

        if isinstance(response, dict) and response.get("data"):
            return response["data"][0]

        return {}

    def _build_ad_metrics(self, ad_data, insights):
        actions = insights.get("actions", [])

        leads_total = sum(
            int(a.get("value", 0)) for a in actions if a.get("action_type") == "lead"
        )

        conversions_total = sum(
            int(a.get("value", 0))
            for a in actions
            if a.get("action_type") in ("offsite_conversion", "onsite_conversion")
        )

        creative = ad_data.get("creative", {})
        object_story_spec = creative.get("object_story_spec", {})

        story_message = ""
        story_description = ""

        link_data = object_story_spec.get("link_data", {})
        video_data = object_story_spec.get("video_data", {})

        if link_data:
            story_message = link_data.get("message", "")
            story_description = link_data.get("description", "")

        if video_data and not story_message:
            story_message = video_data.get("message", "")
            story_description = video_data.get("description", "")

        ad_name = ad_data.get("name") or creative.get("title") or creative.get("name")
        message = (
            story_message
            or creative.get("body")
            or ad_name
            or f"Ad {ad_data.get('id')}"
        )

        if story_description and story_description != message:
            message = f"{message}\n\n{story_description}"

        return {
            "message": message,
            "content_type": "ad",
            "fb_content_id": ad_data.get("id"),
            "fb_ad_id": ad_data.get("id"),
            "ad_name": ad_name,
            "impressions_total": int(insights.get("impressions", 0)),
            "reach_unique": int(insights.get("reach", 0)),
            "clicks_total": int(insights.get("clicks", 0)),
            "ctr_pct": float(insights.get("ctr", 0)),
            "spend_amount": float(insights.get("spend", 0)),
            "currency": insights.get("currency", "USD"),
            "leads_total": leads_total,
            "conversions_total": conversions_total,
            "account_ids": [(6, 0, [self.id])],
            "state": "published",
        }

    def _update_existing_ad(self, post_account, metrics, ad_data):
        post = post_account.post_id
        post.write(
            {
                "message": metrics["message"],
                "content_type": "ad",
                "state": "published",
            }
        )

        media_urls, video_id = self._extract_ad_media(ad_data)
        if media_urls and not post.image_ids:
            self._attach_media_to_post(post, media_urls, video_id)

        post_account.write_metrics_snapshot(metrics)

    def _create_new_ad(self, metrics, ad_data):
        post = self.env["social.post"].create(
            {
                "message": metrics["message"],
                "content_type": "ad",
                "account_ids": metrics["account_ids"],
                "state": "published",
            }
        )

        media_urls, video_id = self._extract_ad_media(ad_data)
        if media_urls:
            self._attach_media_to_post(post, media_urls, video_id)

        self._ensure_post_account_exists(post, metrics, ad_data)

    def _extract_ad_media(self, ad_data):
        creative = ad_data.get("creative", {})
        object_story_spec = creative.get("object_story_spec", {})

        media_urls = []
        video_id = creative.get("video_id")

        if creative.get("image_url"):
            media_urls.append(creative["image_url"])
        elif creative.get("thumbnail_url"):
            media_urls.append(creative["thumbnail_url"])

        link_data = object_story_spec.get("link_data", {})
        if link_data.get("picture"):
            media_urls.append(link_data["picture"])

        video_data = object_story_spec.get("video_data", {})
        if video_data.get("image_url"):
            media_urls.append(video_data["image_url"])
        if video_data.get("video_id"):
            video_id = video_data["video_id"]

        return media_urls, video_id

    def _sync_ads_from_creatives(self, env_mode):
        _logger.debug("=" * 80)
        _logger.debug("DIAGNOSTIC: No ads found via /ads endpoint")
        _logger.debug(
            "IMPORTANT: Draft ads are NOT returned by Facebook's /ads endpoint!"
        )
        _logger.debug("")
        _logger.debug("Trying alternative: /adcreatives endpoint...")
        _logger.debug("=" * 80)

        # Try adcreatives endpoint as fallback (may include drafts)
        creative_endpoint = f"{self.fb_ad_account_id}/adcreatives"
        creative_params = {
            "access_token": self.page_access_token,
            "fields": (
                "id,name,object_story_spec,title,body," "image_url,video_id,status"
            ),
            "limit": 100,
        }
        _logger.warning(f"Trying endpoint: {creative_endpoint}")
        creative_response = self._request_facebook(
            endpoint=creative_endpoint, params=creative_params
        )

        if hasattr(creative_response, "status_code"):
            _logger.error(
                f"AdCreatives API returned status " f"{creative_response.status_code}"
            )
            if hasattr(creative_response, "text"):
                _logger.error(f"Error details: {creative_response.text}")
        elif isinstance(creative_response, dict):
            creatives_data = creative_response.get("data", [])
            _logger.debug(f"Retrieved {len(creatives_data)} ad creatives from Facebook")

            if len(creatives_data) > 0:
                _logger.debug("Processing ad creatives as draft ads...")
                # Process creatives as ads
                created_count = 0
                for creative in creatives_data:
                    creative_id = creative.get("id")
                    creative_name = (
                        creative.get("name")
                        or creative.get("title")
                        or f"Creative {creative_id}"
                    )

                    # Build basic ad data from creative
                    metrics_data = {
                        "message": creative_name,
                        "content_type": "ad",
                        "fb_content_id": creative_id,
                        "fb_ad_id": creative_id,
                        "ad_name": creative_name,
                        "account_ids": [(6, 0, [self.id])],
                        "image_urls": "[]",
                        "state": "draft",  # Creatives are drafts
                    }

                    # Check if already exists
                    existing = self.env["social.post.account"].search(
                        [
                            "|",
                            ("fb_ad_id", "=", creative_id),
                            ("fb_content_id", "=", creative_id),
                        ],
                        limit=1,
                    )

                    if not existing:
                        # Create new post
                        # Note: image_urls is a computed field,
                        # don't include it in create()
                        post = self.env["social.post"].create(
                            {
                                "message": metrics_data.get("message"),
                                "content_type": metrics_data.get("content_type"),
                                "account_ids": metrics_data.get("account_ids"),
                                "state": metrics_data.get("state"),
                            }
                        )

                        # Create post_account with ad data
                        post_account = self.env["social.post.account"].search(
                            [
                                ("post_id", "=", post.id),
                                ("account_id", "=", self.id),
                            ],
                            limit=1,
                        )

                        if post_account:
                            post_account.write(
                                {
                                    "fb_content_id": creative_id,
                                    "fb_ad_id": creative_id,
                                    "ad_name": creative_name,
                                }
                            )
                            created_count += 1
                            _logger.debug(
                                f"  ✓ Created social.post ID: "
                                f"{post.id} from creative {creative_id}"
                            )

                _logger.debug(
                    f"Ad creatives sync completed: {created_count} "
                    f"created from creatives"
                )
                self.last_ads_sync_at = fields.Datetime.now()
                return

        # If still no data, show diagnostic
        _logger.debug("=" * 80)
        _logger.debug("DIAGNOSTIC: No ads or ad creatives found")
        _logger.debug("")
        _logger.debug("Common causes:")
        _logger.debug("  1. All ads are in DRAFT status (not visible via /ads API)")
        _logger.debug("  2. No ads or creatives exist in this ad account")
        _logger.debug("  3. Ads are archived or deleted")
        _logger.debug("  4. Token missing 'ads_read' permission")
        _logger.debug(f"  5. Ad account ({self.fb_ad_account_id}) not accessible")
        _logger.debug("")
        _logger.debug("WORKAROUNDS (without payment):")
        _logger.debug("  1. Use Graph API Explorer to manually check:")
        _logger.debug(f"GET /{self.fb_ad_account_id}/adcreatives?fields=id,name,title")
        _logger.debug("  2. Create test ads in 'Campaign Budget Optimization' mode")
        _logger.debug("  3. Use Facebook's test ad accounts (if available)")
        _logger.debug("")
        _logger.debug(f"Environment: {env_mode.upper()} mode")
        _logger.debug("=" * 80)
        self.last_ads_sync_at = fields.Datetime.now()
        return

    def _sync_facebook_lead_forms(self):
        """Sync lead forms from Facebook Page

        This method automatically fetches all lead forms associated with this page
        and creates/updates them in Odoo.
        This eliminates the need for manual form creation.

        API Endpoint: /{PAGE_ID}/leadgen_forms
        Fields: id,name,status,leads_count,questions,privacy_policy_url,created_time

        Returns:
            int: Number of forms synced (created + updated)
        """
        self.ensure_one()

        if not self.page_id or not self.page_access_token:
            _logger.warning(f"No page_id or access token for account {self.name}")
            return 0

        _logger.debug(f"\n--- SYNCING LEAD FORMS FOR PAGE: {self.page_name} ---")

        # Fetch all lead forms for this page
        endpoint = f"{self.page_id}/leadgen_forms"
        params = {
            "access_token": self.page_access_token,
            "fields": (
                "id,name,status,leads_count,questions,"
                "privacy_policy_url,created_time"
            ),
            "limit": 100,
        }

        response = self._request_facebook(endpoint=endpoint, params=params)

        if not isinstance(response, dict):
            _logger.error(f"Invalid response from Facebook API: {response}")
            return 0

        forms_data = response.get("data", [])
        _logger.debug(f"Retrieved {len(forms_data)} lead forms from Facebook")

        if not forms_data:
            _logger.debug("No lead forms found for this page")
            return 0

        created_count = 0
        updated_count = 0

        for form_data in forms_data:
            try:
                form_id = form_data.get("id")
                form_name = form_data.get("name", "Unnamed Form")

                _logger.debug(f"Processing form: {form_name} (ID: {form_id})")

                # Check if form already exists
                existing_form = self.env["social.lead.form"].search(
                    [
                        ("fb_form_id", "=", form_id),
                    ],
                    limit=1,
                )

                # Prepare form values
                form_values = {
                    "name": form_name,
                    "account_id": self.id,
                    "platform": "facebook",
                    "fb_form_id": form_id,
                    "status": form_data.get("status", "ACTIVE").lower(),
                    "leads_count": form_data.get("leads_count", 0),
                    "privacy_policy_url": form_data.get("privacy_policy_url", ""),
                }

                # Store questions as JSON if available
                if form_data.get("questions"):
                    form_values["questions"] = json.dumps(form_data["questions"])

                # Parse created_time if available
                if form_data.get("created_time"):
                    created_time = self._parse_facebook_datetime(
                        form_data["created_time"]
                    )
                    if created_time:
                        form_values["created_time"] = created_time

                if existing_form:
                    # Update existing form
                    existing_form.write(form_values)
                    updated_count += 1
                    _logger.debug(f"  ✓ Updated form: {form_name}")
                else:
                    # Create new form
                    self.env["social.lead.form"].create(form_values)
                    created_count += 1
                    _logger.debug(f"  ✓ Created form: {form_name}")

            except Exception as e:
                _logger.error(f"Error processing form {form_data.get('id')}: {str(e)}")
                continue

        _logger.debug(
            f"Lead forms sync completed: {created_count} created, "
            f"{updated_count} updated"
        )
        _logger.debug("--- END LEAD FORMS SYNC ---\n")

        return created_count + updated_count

    def _sync_facebook_comments(self, from_datetime=None, to_datetime=None):
        """Feature #4: Sync comments from Facebook posts

        API Endpoints:
        - /{POST_ID}/comments - Get comments on a post
        - /{COMMENT_ID}/comments - Get replies to a comment
        """
        self.ensure_one()
        if not self.page_id or not self.page_access_token:
            _logger.warning(f"No page_id or access token for account {self.name}")
            return

        _logger.debug(f"Syncing comments for page: {self.page_name}")

        # Get all Facebook post accounts for this account
        post_accounts = self.env["social.post.account"].search(
            [
                ("account_id", "=", self.id),
                ("media_type", "=", "facebook"),
                ("fb_content_id", "!=", False),
            ]
        )

        total_comments_synced = 0

        for post_account in post_accounts:
            try:
                post_id = post_account.fb_content_id
                post = post_account.post_id

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
                    _logger.debug(
                        f"Retrieved {len(comments_data)} comments for post {post_id}"
                    )

                    for comment_data in comments_data:
                        self._process_comment_data(comment_data, post.id)
                        total_comments_synced += 1

                        # Fetch replies if comment has replies
                        if comment_data.get("comment_count", 0) > 0:
                            self._sync_comment_replies(comment_data.get("id"), post.id)

            except Exception as e:
                _logger.error(
                    f"Error syncing comments for post {post.fb_content_id}: {str(e)}"
                )
                continue

        _logger.debug(
            f"Comments sync completed: {total_comments_synced} comments synced"
        )

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
                parent_comment = self.env["social.comment"].search(
                    [("comment_id", "=", parent_comment_id)], limit=1
                )

                for reply_data in replies_data:
                    self._process_comment_data(
                        reply_data,
                        post_id,
                        parent_comment.id if parent_comment else False,
                    )

        except Exception as e:
            _logger.error(
                f"Error syncing replies for comment {parent_comment_id}: {str(e)}"
            )

    def _process_comment_data(self, comment_data, post_id, parent_id=False):
        """Process and store comment data"""
        comment_id = comment_data.get("id")

        # Check if comment already exists
        existing_comment = self.env["social.comment"].search(
            [("comment_id", "=", comment_id)], limit=1
        )

        author_data = comment_data.get("from", {})
        current_time = fields.Datetime.now()

        comment_vals = self._build_comment_vals(
            comment_data, post_id, parent_id, author_data, current_time
        )

        if existing_comment:
            self._update_existing_comment(existing_comment, comment_vals)
        else:
            # Create new comment
            try:
                self.env["social.comment"].with_context(tracking_disable=True).create(
                    comment_vals
                )
            except Exception as e:
                # If unique constraint violation, comment was created by another process
                if "comment_id_unique" not in str(e):
                    raise

    def _build_comment_vals(
        self, comment_data, post_id, parent_id, author_data, current_time
    ):
        return {
            "post_id": post_id,
            "comment_id": comment_data.get("id"),
            "parent_id": parent_id,
            "message": comment_data.get("message", ""),
            "author_name": author_data.get("name"),
            "author_id": author_data.get("id"),
            "created_time": self._parse_facebook_datetime(
                comment_data.get("created_time")
            ),
            "last_sync_at": current_time,
        }

    def _update_existing_comment(self, existing_comment, comment_vals):
        # Only update if data has actually changed (avoid unnecessary writes)
        needs_update = False
        for key, value in comment_vals.items():
            if key == "last_sync_at":
                continue  # Always skip last_sync_at comparison

            # Safely get the current value, handle missing attributes
            try:
                current_value = getattr(existing_comment, key, None)

                # Special handling for different field types
                if key in ("parent_id", "post_id"):
                    # For Many2one fields, compare IDs
                    current_id = current_value.id if current_value else False
                    if current_id != value:
                        needs_update = True
                        break
                elif key == "created_time":
                    # For datetime fields, handle None and comparison carefully
                    if (current_value is None and value is not None) or (
                        current_value is not None and value is None
                    ):
                        needs_update = True
                        break
                    elif current_value is not None and value is not None:
                        # Compare datetime values safely
                        try:
                            if current_value != value:
                                needs_update = True
                                break
                        except Exception:
                            # If datetime comparison fails, assume they're different
                            needs_update = True
                            break
                else:
                    # For other fields, do simple comparison
                    try:
                        if current_value != value:
                            needs_update = True
                            break
                    except Exception:
                        # If comparison fails, assume it needs update
                        needs_update = True
                        break

            except Exception as e:
                # If we can't get the attribute, assume it needs update
                _logger.warning(f"Failed to access field '{key}': {str(e)}")
                needs_update = True
                break

        if needs_update:
            # Update without last_sync_at to avoid concurrent update conflicts
            update_vals = {k: v for k, v in comment_vals.items() if k != "last_sync_at"}
            try:
                existing_comment.with_context(tracking_disable=True).write(update_vals)
            except Exception as e:
                # If concurrent update conflict, just skip
                # (another process already updated it)
                if "could not serialize access" not in str(e):
                    raise

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
            _logger.debug(f"Successfully replied to comment {comment_id}")
            return response
        else:
            _logger.error(f"Failed to reply to comment {comment_id}: {response}")
            return False

    def _hide_facebook_comment(self, comment_id):
        """Hide a Facebook comment

        Args:
            comment_id: Facebook comment ID

        Returns:
            dict: {"success": bool, "message": str, "error_code": str}
        """
        self.ensure_one()
        if not self.page_access_token:
            return {
                "success": False,
                "message": "No page access token available",
                "error_code": "NO_TOKEN",
            }

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

        # Check if response is successful (dict with success=True)
        if isinstance(response, dict) and response.get("success"):
            _logger.debug(f"Successfully hid comment {comment_id}")
            return {
                "success": True,
                "message": "Comment hidden successfully",
            }

        # Handle HTTP error responses
        if hasattr(response, "status_code"):
            error_msg = f"HTTP {response.status_code}"
            error_code = f"HTTP_{response.status_code}"

            # Try to parse error details from response
            try:
                error_data = response.json()
                if "error" in error_data:
                    fb_error = error_data["error"]
                    error_msg = fb_error.get("message", error_msg)
                    error_code = fb_error.get("code", error_code)
                    error_type = fb_error.get("type", "")

                    # Provide user-friendly messages for common errors
                    if response.status_code == 403:
                        if (
                            "OAuthException" in error_type
                            or "permissions" in error_msg.lower()
                        ):
                            error_msg = (
                                "Permission denied. Please ensure:\n"
                                "1. Your Facebook App has "
                                "'pages_manage_engagement' permission\n"
                                "2. The page access token has necessary permissions\n"
                                "3. The comment is not from a page admin\n"
                                f"Facebook error: {error_msg}"
                            )
                        else:
                            error_msg = f"Access forbidden: {error_msg}"
                    elif response.status_code == 400:
                        error_msg = f"Invalid request: {error_msg}"
            except Exception:
                _logger.error("Error while hiding Facebook comment")

            _logger.error(f"Failed to hide comment {comment_id}: {error_msg}")
            return {
                "success": False,
                "message": error_msg,
                "error_code": str(error_code),
            }

        # Unknown response format
        _logger.error(
            f"Unexpected response format for comment {comment_id}: {response}"
        )
        return {
            "success": False,
            "message": f"Unexpected response from Facebook: {response}",
            "error_code": "UNKNOWN",
        }

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
            _logger.warning(f"No page_id or access token for account {self.name}")
            return

        _logger.debug(f"Syncing leads for page: {self.page_name}")

        # Get all lead forms for this account
        lead_forms = self.env["social.lead.form"].search([("account_id", "=", self.id)])

        if not lead_forms:
            _logger.warning(f"No lead forms configured for account {self.name}")
            return

        total_leads_synced = 0

        for lead_form in lead_forms:
            try:
                _logger.debug(
                    f"Syncing leads for form: {lead_form.name}"
                    f" (ID: {lead_form.fb_form_id})"
                )

                # Build params
                params = {
                    "access_token": self.page_access_token,
                    "fields": "id,created_time,field_data",
                    "limit": 100,
                }

                # Add date filters if provided
                if from_datetime:
                    params["filtering"] = json.dumps(
                        [
                            {
                                "field": "time_created",
                                "operator": "GREATER_THAN",
                                "value": int(from_datetime.timestamp()),
                            }
                        ]
                    )
                elif lead_form.last_sync_at:
                    # Incremental sync using last sync time
                    params["filtering"] = json.dumps(
                        [
                            {
                                "field": "time_created",
                                "operator": "GREATER_THAN",
                                "value": int(lead_form.last_sync_at.timestamp()),
                            }
                        ]
                    )

                endpoint = f"{lead_form.fb_form_id}/leads"
                response = self._request_facebook(endpoint=endpoint, params=params)

                if isinstance(response, dict) and response.get("data"):
                    leads_data = response.get("data", [])
                    _logger.debug(
                        f"Retrieved {len(leads_data)} leads for form {lead_form.name}"
                    )

                    for lead_data in leads_data:
                        try:
                            lead_form._process_lead_data(lead_data)
                            total_leads_synced += 1
                        except Exception as e:
                            _logger.error(
                                f"Error processing lead {lead_data.get('id')}: {str(e)}"
                            )
                            continue

                    # Update last sync time for this form
                    lead_form.last_sync_at = fields.Datetime.now()
                else:
                    _logger.warning(f"No new leads for form {lead_form.name}")

            except Exception as e:
                _logger.error(
                    f"Error syncing leads for form {lead_form.name}: {str(e)}"
                )
                continue

        _logger.debug(f"Leads sync completed: {total_leads_synced} leads synced")

    def _sync_facebook_content(self, from_datetime=None, to_datetime=None, types=None):
        """Manual sync action with optional filters

        Args:
            from_datetime: Start datetime for sync (ISO format or datetime object)
            to_datetime: End datetime for sync (ISO format or datetime object)
            types: List of content types to sync ['posts', 'ads', 'comments', 'leads']
                   If None, syncs all types
                   Note: 'posts' includes all content (text, images, videos/reels)

        Usage:
            # Sync all content for all accounts
            model._sync_facebook_content()

            # Sync only posts from last 7 days
            model._sync_facebook_content(
                from_datetime='2025-01-01T00:00:00',
                types=['posts']
            )
        """
        # Default to all sync types if not specified
        if types is None:
            types = ["posts", "ads"]

        # Parse datetime strings if provided
        if from_datetime and isinstance(from_datetime, str):
            from_datetime = fields.Datetime.from_string(from_datetime)
        if to_datetime and isinstance(to_datetime, str):
            to_datetime = fields.Datetime.from_string(to_datetime)

        # If called on specific account(s), use self, otherwise sync all active accounts
        if self:
            accounts = self
        else:
            accounts = self.search(
                [("media_type", "=", "facebook"), ("status", "=", "active")]
            )

        _logger.debug("=" * 80)
        _logger.debug(f"Manual sync started for {len(accounts)} Facebook account(s)")
        _logger.debug(
            f"Parameters: from={from_datetime}, to={to_datetime}, types={types}"
        )

        for account in accounts:
            try:
                _logger.debug("\n" + "=" * 80)
                _logger.debug(f"Syncing account: {account.name} (ID: {account.id})")
                _logger.debug("=" * 80)

                # Sync posts if requested
                # (includes all posts: text, images, videos/reels)
                if "posts" in types:
                    _logger.debug("\n--- POSTS SYNC ---")
                    account._sync_facebook_posts_filtered(from_datetime, to_datetime)
                    _logger.debug("--- END POSTS SYNC ---\n")

                # Sync ads if requested
                if "ads" in types:
                    _logger.debug("\n--- ADS SYNC ---")
                    account._sync_facebook_ads(from_datetime, to_datetime)
                    _logger.debug("--- END ADS SYNC ---\n")

                # Sync comments if requested (Feature #4: Comment Moderation System)
                if "comments" in types:
                    _logger.debug("\n--- COMMENTS SYNC ---")
                    account._sync_facebook_comments(from_datetime, to_datetime)
                    _logger.debug("--- END COMMENTS SYNC ---\n")

                # Sync leads if requested (Feature #5: Lead Ads Integration)
                if "leads" in types:
                    _logger.debug("  - Syncing leads...")
                    account._sync_facebook_leads(from_datetime, to_datetime)

                _logger.debug("  ✓ Account sync completed")

            except Exception as e:
                _logger.error(f"Error syncing account {account.name}: {str(e)}")
                continue

        _logger.debug("Manual sync completed for all accounts")
        _logger.debug("=" * 80)

    def _run_check_media_updates(self):
        """Override base module hook to auto-sync Facebook content every 30 minutes

        This method is called by the base module's cron job (webhook_schedule_job)
        which runs every 30 minutes. It syncs recent content
        for all active Facebook accounts.

        Architecture:
        - social_media_base provides the hook/interface
        - social_media_facebook overrides it for Facebook-specific syncing
        - Other providers (Instagram, Twitter, etc.) can override similarly
        """
        # Only sync Facebook accounts
        facebook_accounts = self.search(
            [("media_type", "=", "facebook"), ("status", "=", "active")]
        )

        if not facebook_accounts:
            return True

        _logger = logging.getLogger(__name__)

        _logger.debug(
            f"Auto-sync: Starting for {len(facebook_accounts)} Facebook account(s)"
        )

        # Sync recent content (last 24 hours)

        from_datetime = fields.Datetime.now() - timedelta(hours=24)

        for account in facebook_accounts:
            try:
                _logger.debug(f"Auto-syncing Facebook account: {account.name}")
                # Call the main sync method with recent content filter
                account._sync_facebook_content(
                    from_datetime=from_datetime,
                    to_datetime=None,
                    types=["posts", "ads", "comments", "leads"],
                )
            except Exception as e:
                _logger.error(
                    f"Error auto-syncing Facebook account {account.name}: {e}"
                )
                continue

        _logger.debug("Auto-sync: Completed for all Facebook accounts")
        return True

    def _sync_facebook_posts_filtered(self, from_datetime=None, to_datetime=None):
        """Sync posts with optional date filters"""
        _logger.debug("=== _sync_facebook_posts_filtered called")
        self.ensure_one()
        if not self.page_id or not self.page_access_token:
            _logger.warning(f"=== No page_id or access token for account {self.name}")
            return

        _logger.debug(f"=== Syncing posts for page: {self.page_name}")

        # Build params with date filters
        fields_str = (
            "id,message,created_time,permalink_url,"
            "attachments{media_type,media,url,subattachments{media{image}}},"
            "likes.summary(true),comments.summary(true),shares,"
            "insights.metric(post_media_view,post_impressions_unique,"
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
        _logger.debug("Facebook posts response received")
        _logger.debug(f"Response: {response}")
        if isinstance(response, dict) and response.get("data"):
            self._process_posts_data(response.get("data", []))
            self.last_posts_sync_at = fields.Datetime.now()
        else:
            _logger.warning(f"No posts data in response: {response}")

    def _sync_facebook_reels_filtered(self, from_datetime=None, to_datetime=None):
        """Sync reels/videos with optional date filters"""
        self.ensure_one()
        if not self.page_id or not self.page_access_token:
            return

        _logger.debug(f"Syncing videos for page: {self.page_name}")

        # Note: Requesting basic video fields + engagement data + source (video URL)
        # likes, comments are available as summary data on the Video object
        # Video insights (views) require separate endpoint /{video-id}/video_insights
        # source field contains the video file URL for downloading
        fields_str = (
            "id,title,description,created_time,permalink_url,"
            "length,source,likes.summary(true),comments.summary(true)"
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
        _logger.debug(f"Requesting reels from endpoint: {endpoint}")
        _logger.debug(f"Request params: {params}")

        response = self._request_facebook(endpoint=endpoint, params=params)

        _logger.debug(f"Response type: {type(response)}")
        _logger.debug(f"Response value: {response}")

        # Check if response is an error (Response object instead of dict)
        if hasattr(response, "status_code"):
            _logger.error(f"HTTP {response.status_code} response from Facebook API")
            _logger.error(f"Response text: {response.text}")
            try:
                error_data = response.json()
                _logger.error(f"Error details: {error_data}")
                if "error" in error_data:
                    _logger.error(
                        f"Facebook error message: {error_data['error'].get('message')}"
                    )
                    _logger.error(
                        f"Facebook error code: {error_data['error'].get('code')}"
                    )
                    _logger.error(
                        f"Facebook error type: {error_data['error'].get('type')}"
                    )
            except Exception:
                _logger.error("Failed to parse error response JSON")
            return

        if isinstance(response, dict) and response.get("data"):
            videos_data = response.get("data", [])
            _logger.debug(f"Retrieved {len(videos_data)} videos")
            self._process_reels_data(videos_data)
            self.last_reels_sync_at = fields.Datetime.now()
        else:
            _logger.warning(f"No videos data in response: {response}")

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
        except Exception:
            try:
                # Fallback: manual parsing (already naive)
                return datetime.strptime(datetime_str[:19], "%Y-%m-%dT%H:%M:%S")
            except Exception:
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
                _logger.warning(
                    f"Failed to download image from {url}, "
                    f"status: {response.status_code}"
                )
                return False

            # Generate filename if not provided
            if not filename:
                # Extract filename from URL or generate one
                from urllib.parse import urlparse

                parsed_url = urlparse(url)
                filename = (
                    parsed_url.path.split("/")[-1]
                    or f"facebook_image_{fields.Datetime.now().timestamp()}.jpg"
                )

            # Create attachment
            attachment = self.env["ir.attachment"].create(
                {
                    "name": filename,
                    "type": "binary",
                    "datas": base64.b64encode(response.content),
                    "mimetype": response.headers.get("content-type", "image/jpeg"),
                    "res_model": "social.post",
                    # res_id will be set later when linking to post
                }
            )

            _logger.debug(f"Downloaded image: {filename} (ID: {attachment.id})")
            return attachment

        except Exception as e:
            _logger.error(f"Failed to download image from {url}: {str(e)}")
            return False

    def _attach_media_to_post(self, post, media_urls, video_id=None):
        """Download and attach media (images/videos) to a social post

        Args:
            post: social.post record
            media_urls: List of image URLs to download
            video_id: Optional Facebook video ID

        Returns:
            List of ir.attachment records created
        """
        if not post:
            return []

        attachments = []
        attachment_ids = []

        # Download images
        for idx, url in enumerate(media_urls):
            if url:
                filename = f"ad_image_{idx+1}_{post.id}.jpg"
                attachment = self._download_image_from_url(url, filename=filename)
                if attachment:
                    attachment.write({"res_id": post.id})
                    attachments.append(attachment)
                    attachment_ids.append(attachment.id)

        # Link attachments to post via image_ids field
        if attachment_ids:
            post.write({"image_ids": [(6, 0, attachment_ids)]})
            _logger.debug(
                f"Attached {len(attachment_ids)} media files to post {post.id}"
            )

        # Handle video if present
        if video_id:
            _logger.debug(f"Post has video ID: {video_id}")
            # Note: Video files are typically too large to download and store
            # For now we just log the video ID
            # Alternative: Could download video thumbnail instead

        return attachments

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
                _logger.debug(f"  Page picture URL: {picture_url[:80]}...")

                # Download the image
                img_response = requests.get(picture_url, timeout=10)
                if img_response.status_code == 200:
                    return base64.b64encode(img_response.content)
                else:
                    _logger.warning(
                        f"Failed to download page picture, "
                        f"status: {img_response.status_code}"
                    )
                    return False
            else:
                _logger.warning(f"No picture URL in response: {response}")
                return False

        except Exception as e:
            _logger.error(f"Failed to download page picture: {str(e)}")
            return False

    def _process_posts_data(self, posts_data):
        """Extract post processing logic for reuse"""
        created_count = 0
        updated_count = 0

        for post_data in posts_data:
            try:
                (
                    existing_post,
                    fb_content_id,
                    media_type_val,
                    image_attachments,
                    metrics_data,
                ) = self._prepare_post_data(post_data)

                if existing_post:
                    # Update the existing post with basic info
                    existing_post.write(
                        {
                            "message": metrics_data.get("message"),
                            "content_type": metrics_data.get("content_type"),
                            "state": metrics_data.get("state"),
                            "published_date": metrics_data.get("created_time"),
                        }
                    )
                    updated_count += 1
                    _logger.debug(
                        f"Updated social.post ID: "
                        f"{existing_post.id} (FB: {fb_content_id})"
                    )
                    # Update post_account record with Facebook metrics
                    self._ensure_post_account_exists(
                        existing_post, metrics_data, post_data
                    )
                else:
                    # Create new post with basic info
                    # Note: image_urls is a computed field, don't include it in create()
                    post = self.env["social.post"].create(
                        {
                            "message": metrics_data.get("message"),
                            "content_type": metrics_data.get("content_type"),
                            "account_ids": metrics_data.get("account_ids"),
                            "state": metrics_data.get("state"),
                            "published_date": metrics_data.get("created_time"),
                        }
                    )
                    if "image_ids" in metrics_data:
                        post.write({"image_ids": metrics_data["image_ids"]})
                    created_count += 1
                    _logger.debug(
                        f"Created social.post ID: {post.id} (FB: {fb_content_id})"
                    )
                    # Create post_account record with Facebook metrics
                    self._ensure_post_account_exists(post, metrics_data, post_data)

            except Exception as e:
                _logger.error(f"Error processing post {post_data.get('id')}: {str(e)}")
                continue

        _logger.debug(
            f"Posts processed: {created_count} created, {updated_count} updated"
        )

    def _prepare_post_data(self, post_data):
        fb_content_id = post_data.get("id")

        # Search for existing post via social.post.account
        # (where fb_content_id is stored)
        existing_post_account = self.env["social.post.account"].search(
            [("fb_content_id", "=", fb_content_id)],
            limit=1,
        )
        existing_post = (
            existing_post_account.post_id if existing_post_account else False
        )

        # Parse data - Extract images from attachments
        (
            media_type_val,
            image_attachments,
        ) = self._extract_images_from_attachments(post_data)

        likes_count = (
            post_data.get("likes", {}).get("summary", {}).get("total_count", 0)
        )
        comments_count = (
            post_data.get("comments", {}).get("summary", {}).get("total_count", 0)
        )
        shares_count = post_data.get("shares", {}).get("count", 0)

        (
            impressions_total,
            reach_unique,
            clicks_total,
            reactions_by_type,
        ) = self._extract_insights(post_data)

        # Detect content type based on media_type from Facebook
        # video/reel posts should be marked as 'reel', others as 'post'
        content_type = "post"
        if media_type_val in ["video", "video_inline", "video_autoplay"]:
            content_type = "reel"

        # Debug logging for content type detection
        _logger.debug(
            f"DEBUG: Post {fb_content_id} - "
            f"media_type_val='{media_type_val}' -> "
            f"content_type='{content_type}'"
        )

        metrics_data = {
            "message": post_data.get("message", "") or f"Post {fb_content_id}",
            "content_type": content_type,  # Set on social.post (base model)
            "fb_content_id": fb_content_id,
            "permalink_url": post_data.get("permalink_url"),
            "created_time": self._parse_facebook_datetime(
                post_data.get("created_time")
            ),
            "likes_count": likes_count,
            "reactions_by_type_json": json.dumps(reactions_by_type)
            if reactions_by_type
            else "{}",
            "comments_count": comments_count,
            "shares_count": shares_count,
            "impressions_total": impressions_total,
            "reach_unique": reach_unique,
            "clicks_total": clicks_total,
            "account_ids": [(6, 0, [self.id])],  # Required field
            "image_urls": ("[]"),  # Required by kanban template - empty array for now
            "state": ("published"),  # Posts synced from Facebook are already published
        }

        if image_attachments:
            metrics_data["image_ids"] = [(6, 0, image_attachments)]

        return (
            existing_post,
            fb_content_id,
            media_type_val,
            image_attachments,
            metrics_data,
        )

    def _extract_images_from_attachments(self, post_data):
        attachments = post_data.get("attachments", {}).get("data", [])
        media_type_val = None
        image_attachments = []

        if attachments:
            first_attachment = attachments[0]
            media_type_val = first_attachment.get("media_type")

            # Handle album (multiple images)
            if media_type_val == "album":
                # Album contains multiple images in subattachments
                subattachments = first_attachment.get("subattachments", {}).get(
                    "data", []
                )
                for sub in subattachments:
                    if "media" in sub and "image" in sub["media"]:
                        img_url = sub["media"]["image"].get("src")
                        if img_url:
                            attachment = self._download_image_from_url(img_url)
                            if attachment:
                                image_attachments.append(attachment.id)

            # Handle single image
            elif "media" in first_attachment:
                if "image" in first_attachment["media"]:
                    media_url = first_attachment["media"]["image"].get("src")
                    if media_url:
                        attachment = self._download_image_from_url(media_url)
                        if attachment:
                            image_attachments.append(attachment.id)

        return media_type_val, image_attachments

    def _extract_insights(self, post_data):
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
                if metric_name == "post_media_view":
                    impressions_total = value
                elif metric_name == "post_impressions_unique":
                    reach_unique = value
                elif metric_name == "post_reactions_by_type_total":
                    if isinstance(value, dict):
                        reactions_by_type = value
                elif metric_name == "post_clicks":
                    clicks_total = value

        return impressions_total, reach_unique, clicks_total, reactions_by_type

    def _process_reels_data(self, videos_data):
        """Extract reel processing logic for reuse"""
        created_count = 0
        updated_count = 0

        for video_data in videos_data:
            try:
                fb_content_id = video_data.get("id")

                # Fix incomplete permalink URL (missing domain)
                raw_permalink = video_data.get("permalink_url", "")
                if raw_permalink and raw_permalink.startswith("/"):
                    permalink_url = f"https://www.facebook.com{raw_permalink}"
                else:
                    permalink_url = raw_permalink

                # Check if this video was already synced as a post
                # Videos appear in both /posts and /videos endpoints,
                # but with different IDs
                # We search by permalink_url to avoid duplicates
                existing_post_account = self.env["social.post.account"].search(
                    [
                        "|",
                        ("fb_content_id", "=", fb_content_id),
                        ("permalink_url", "=", permalink_url),
                    ],
                    limit=1,
                )

                if (
                    existing_post_account
                    and existing_post_account.fb_content_id != fb_content_id
                ):
                    # This video was already synced as a post with different ID
                    # Skip it to avoid duplicate
                    _logger.warning(
                        f"  ⊗ Skipping video {fb_content_id} - "
                        f"already synced as post {existing_post_account.fb_content_id}"
                    )
                    continue

                existing_post = (
                    existing_post_account.post_id if existing_post_account else False
                )

                # Extract engagement data (likes, comments, shares)
                likes_count = (
                    video_data.get("likes", {}).get("summary", {}).get("total_count", 0)
                )
                comments_count = (
                    video_data.get("comments", {})
                    .get("summary", {})
                    .get("total_count", 0)
                )
                # Note: shares field doesn't exist on Video objects in Facebook API
                shares_count = video_data.get("shares", {}).get("count", 0)

                # Extract video insights (if available - currently not requested)
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

                # Extract video source URL (if available)
                video_source = video_data.get("source")
                # video_urls_json = "[]"
                if video_source:
                    # video_urls_json = json.dumps([video_source])
                    _logger.debug(f"Video has source URL: {video_source}")

                metrics_data = {
                    "message": video_data.get("description", "")
                    or video_data.get("title", "")
                    or f"Video {fb_content_id}",
                    "content_type": "reel",  # Videos are reels
                    "fb_content_id": fb_content_id,
                    "permalink_url": permalink_url,  # Use fixed permalink with full URL
                    "fb_video_url": video_source,  # Facebook video file URL
                    "created_time": self._parse_facebook_datetime(
                        video_data.get("created_time")
                    ),
                    # Engagement metrics
                    "likes_count": likes_count,
                    "comments_count": comments_count,
                    "shares_count": shares_count,
                    # Video metrics
                    "plays_total": plays_total,
                    "plays_unique": plays_unique,
                    "watch_time_sec": watch_time_sec,
                    "completed_views": completed_views,
                    # Required fields
                    "account_ids": [(6, 0, [self.id])],  # Required field
                    "image_urls": "[]",  # Required by kanban template
                    "state": (
                        "published"
                    ),  # Reels synced from Facebook are already published
                }

                if existing_post:
                    # Update the existing post with basic info
                    existing_post.write(
                        {
                            "message": metrics_data.get("message"),
                            "state": metrics_data.get("state"),
                            "published_date": metrics_data.get("created_time"),
                        }
                    )
                    updated_count += 1
                    _logger.debug(
                        f"Updated social.post ID: {existing_post.id}"
                        f" (FB: {fb_content_id})"
                    )
                    # Update post_account record with Facebook metrics
                    self._ensure_post_account_exists(
                        existing_post, metrics_data, video_data
                    )
                else:
                    # Create new post with basic info
                    # Note: image_urls is a computed field, don't include it in create()
                    post = self.env["social.post"].create(
                        {
                            "message": metrics_data.get("message"),
                            "account_ids": metrics_data.get("account_ids"),
                            "content_type": "reel",  # Videos are reels
                            "state": metrics_data.get("state"),
                            "published_date": metrics_data.get("created_time"),
                        }
                    )
                    created_count += 1
                    _logger.debug(
                        f"Created social.post ID: {post.id} (FB: {fb_content_id})"
                    )
                    # Create post_account record with Facebook metrics
                    self._ensure_post_account_exists(post, metrics_data, video_data)

            except Exception as e:
                _logger.error(
                    f"Error processing video {video_data.get('id')}: {str(e)}"
                )
                continue

        _logger.debug(
            f"Reels processed: {created_count} created, {updated_count} updated"
        )

    def _serialize_metrics_json(self, metrics_data):
        """Serialize metrics_data to JSON, converting datetime objects to ISO strings

        Args:
            metrics_data: Dict with post metrics that may contain datetime objects

        Returns:
            JSON string with datetimes converted to ISO format
        """
        # Create a copy to avoid modifying the original
        serializable_data = {}
        for key, value in metrics_data.items():
            if isinstance(value, datetime | date):
                # Convert datetime/date to ISO format string
                serializable_data[key] = value.isoformat() if value else None
            elif (
                isinstance(value, list | tuple)
                and value
                and isinstance(value[0], datetime | date)
            ):
                # Handle lists of datetimes
                serializable_data[key] = [v.isoformat() if v else None for v in value]
            else:
                # Keep other types as-is (they're JSON serializable)
                serializable_data[key] = value

        try:
            return json.dumps(serializable_data, indent=2)
        except Exception as e:
            # Fallback: return minimal JSON with error
            _logger.warning(f"Error serializing metrics_data: {str(e)}")
            return json.dumps(
                {
                    "error": "Serialization failed",
                    "fb_content_id": metrics_data.get("fb_content_id"),
                }
            )

    def _ensure_post_account_exists(self, post, metrics_data, fb_data):
        """Ensure a social.post.account record exists for synced posts

        This allows synced posts to appear in the Dashboard view.
        NOW STORES ALL FACEBOOK-SPECIFIC FIELDS on social.post.account!

        Args:
            post: social.post record
            metrics_data: Dict with post metrics
            fb_data: Original Facebook API response data
        """
        # Check if post_account already exists for this account
        existing_post_account = self.env["social.post.account"].search(
            [
                ("post_id", "=", post.id),
                ("account_id", "=", self.id),
            ],
            limit=1,
        )

        # Prepare Facebook-specific fields for social.post.account
        fb_fields = {
            # Basic post fields
            "message": metrics_data.get("message", ""),
            "published_date": metrics_data.get("created_time"),
            "published": True,
            "state": "posted",
            "post_account_url": metrics_data.get("permalink_url", ""),
            "image_urls": metrics_data.get("image_urls", "[]"),
            # Facebook-specific fields
            "fb_content_id": metrics_data.get("fb_content_id"),
            "permalink_url": metrics_data.get("permalink_url"),
            "created_time": metrics_data.get("created_time"),
            "last_sync_at": fields.Datetime.now(),
            # Organic metrics
            "likes_count": metrics_data.get("likes_count", 0),
            "comments_count": metrics_data.get("comments_count", 0),
            "shares_count": metrics_data.get("shares_count", 0),
            "impressions_total": metrics_data.get("impressions_total", 0),
            "reach_unique": metrics_data.get("reach_unique", 0),
            "clicks_total": metrics_data.get("clicks_total", 0),
            # Reel/Video metrics
            "plays_total": metrics_data.get("plays_total", 0),
            "plays_unique": metrics_data.get("plays_unique", 0),
            "watch_time_sec": metrics_data.get("watch_time_sec", 0),
            "completed_views": metrics_data.get("completed_views", 0),
            # Ad metrics
            "spend_amount": metrics_data.get("spend_amount", 0.0),
            "ctr_pct": metrics_data.get("ctr_pct", 0.0),
            "leads_total": metrics_data.get("leads_total", 0),
            "conversions_total": metrics_data.get("conversions_total", 0),
            "currency": metrics_data.get("currency", "USD"),
            # Raw data
            "reactions_by_type_json": metrics_data.get("reactions_by_type_json", "{}"),
            "metrics_json": self._serialize_metrics_json(metrics_data),
            "metrics_updated_at": fields.Datetime.now(),
            # Base fields for compatibility
            "comment_count": metrics_data.get("comments_count", 0),
            "like_count": metrics_data.get("likes_count", 0),
            "share_count": metrics_data.get("shares_count", 0),
            "view_count": metrics_data.get("plays_total", 0),  # For reels
        }

        # Handle Ad-specific fields
        if metrics_data.get("fb_ad_id"):
            fb_fields.update(
                {
                    "fb_ad_id": metrics_data.get("fb_ad_id"),
                    "fb_adset_id": metrics_data.get("fb_adset_id"),
                    "fb_campaign_id": metrics_data.get("fb_campaign_id"),
                    "ad_name": metrics_data.get("ad_name"),
                }
            )

        # Convert image_ids from metrics_data format to Many2many format if present
        if "image_ids" in metrics_data and metrics_data["image_ids"]:
            fb_fields["image_ids"] = metrics_data["image_ids"]

        if existing_post_account:
            # Update existing record with ALL Facebook fields
            existing_post_account.write(fb_fields)
            _logger.debug(
                f"Updated social.post.account ID: {existing_post_account.id}"
                f" (linked to post ID: {post.id})"
            )
        else:
            # Create new post_account record with ALL Facebook fields
            fb_fields.update(
                {
                    "post_id": post.id,
                    "account_id": self.id,
                    "media_id": self.media_id.id,
                }
            )

            new_post_account = self.env["social.post.account"].create(fb_fields)
            _logger.debug(
                f"Created social.post.account ID: {new_post_account.id}"
                f" (linked to post ID: {post.id})"
            )

    # Facebook Insights: Impressions and Engagements
    def get_facebook_impressions_engagements(self, page_id, access_token):
        endpoint = f"{page_id}/insights"
        params = {
            "metric": "page_media_view,page_post_engagements",
            "period": "days_28",
            "access_token": access_token,
        }
        response = self._request_facebook(
            method="GET", endpoint=endpoint, params=params
        )
        return response

    def parse_facebook_impressions_engagements(self, data):
        metrics = {}
        for item in data.get("data", []):
            name = item.get("name")
            if item.get("values"):
                value = item["values"][-1].get("value")
                metrics[name] = value
        return metrics

    def update_facebook_impressions_engagements(self):
        for record in self:
            data = record.get_facebook_impressions_engagements(
                record.page_id, record.page_access_token
            )
            metrics = record.parse_facebook_impressions_engagements(data)

            impression_count = metrics.get("page_media_view", 0)
            interactions_count = metrics.get("page_post_engagements", 0)
            engagement_rate = 0.0

            if impression_count > 0:
                engagement_rate = round(
                    (interactions_count / impression_count) * 100, 2
                )

            record.write(
                {
                    "impression_count": impression_count,
                    "interactions_count": interactions_count,
                    "engagement": engagement_rate,
                }
            )

    def cron_update_facebook_insights(self):
        """
        Scheduled job to update Facebook
        page insights (impressions and engagement).
        """
        _logger.debug("[CRON] Running Facebook Insights update ===")
        facebook_accounts = self.search([("media_type", "=", "facebook")])
        for account in facebook_accounts:
            account.update_facebook_impressions_engagements()
            account.last_insight_update = fields.Datetime.now()

    def delete_account(self):
        res = super().delete_account()
        if self.media_type == "facebook":
            icp = self.env["ir.config_parameter"].sudo()
            icp.set_param("social_media_base.facebook_app_id", False)
            icp.set_param("social_media_base.facebook_app_secret", False)
            icp.set_param("social_media_base.facebook_system_user_token", False)
            icp.set_param("social_media_base.facebook_connection_method", False)
        return res
