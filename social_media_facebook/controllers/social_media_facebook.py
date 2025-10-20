# Copyright 2025 Binhex <https://www.binhex.cloud>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import http
from odoo.http import request


class SocialMediaFacebookController(http.Controller):
    @http.route("/facebook/callback", type="http", auth="public", website=True)
    def facebook_callback(self, **kwargs):
        """Handle Facebook OAuth callback"""
        print("=" * 80)
        print("Facebook OAuth Callback Started")
        print(f"Callback kwargs: {kwargs}")

        authorization_code = kwargs.get("code", False)
        error = kwargs.get("error", False)

        if error:
            print(f"ERROR: Facebook OAuth error: {error}")
            print(f"ERROR: Error description: {kwargs.get('error_description')}")
            return request.redirect(
                "/web#action=social_media_base.social_media_act_window_kanban"
            )

        if authorization_code:
            print(f"Authorization code received: {authorization_code[:20]}...")
            redirect_endpoint_uri = "/facebook/callback"

            # Get app credentials from wizard (like LinkedIn and X do)
            wizard_social_account = (
                request.env["wizard.social.account"]
                .sudo()
                .search(
                    [("media_type", "=", "facebook")],
                    order="id desc",
                    limit=1,
                )
            )

            if wizard_social_account:
                app_id = wizard_social_account.facebook_app_id
                app_secret = wizard_social_account.facebook_app_secret

                print(f"App ID from wizard: {app_id}")
                print(f"App Secret configured: {bool(app_secret)}")
            else:
                print("ERROR: No wizard found with Facebook credentials")
                return request.redirect(
                    "/web#action=social_media_base.social_media_act_window_kanban"
                )

            if not app_id or not app_secret:
                print("ERROR: Facebook app credentials not found in wizard")
                return request.redirect(
                    "/web#action=social_media_base.social_media_act_window_kanban"
                )

            account_model = request.env["social.account"].sudo()
            print("Exchanging authorization code for access token...")
            token = account_model.get_access_token_facebook(
                authorization_code, redirect_endpoint_uri, app_id, app_secret
            )
            print(f"Token response type: {type(token)}")
            print(f"Token response: {token if not isinstance(token, dict) else 'dict with access_token'}")

            if isinstance(token, dict):
                user_access_token = token.get("access_token")
                print(f"User access token received: {user_access_token[:20] if user_access_token else 'None'}...")

                # Fetch available pages
                print("Fetching available Facebook pages...")
                pages = account_model.get_pages_facebook(user_access_token)
                print(f"Found {len(pages)} pages")

                if pages:
                    # Create wizard to let user select pages
                    print("Creating fetch pages wizard...")
                    wizard_model = request.env["wizard.fetch.pages"].sudo()
                    wizard = wizard_model.create(
                        {"user_access_token": user_access_token}
                    )
                    print(f"Wizard created with ID: {wizard.id}")

                    # Create wizard lines for each page
                    for page in pages:
                        print(f"Processing page: {page.get('name')} (ID: {page.get('id')})")
                        page_id = page.get("id", "")
                        # Check if page already connected
                        already_connected = bool(
                            account_model.search(
                                [
                                    ("page_id", "=", page_id),
                                    ("media_type", "=", "facebook"),
                                ],
                                limit=1,
                            )
                        )

                        line = request.env["wizard.fetch.pages.line"].sudo().create(
                            {
                                "wizard_id": wizard.id,
                                "page_id": page_id,
                                "page_name": page.get("name", ""),
                                "page_access_token": page.get("access_token", ""),
                                "selected": not already_connected,
                                "already_connected": already_connected,
                            }
                        )
                        print(f"Created wizard line ID: {line.id}, selected: {not already_connected}, already_connected: {already_connected}")

                    # NOTE: wizard_social_account will be deleted AFTER accounts are created
                    # in wizard_fetch_pages.action_create_accounts() method

                    # Redirect to wizard with proper action format to show form view
                    action_id = request.env.ref('social_media_facebook.action_wizard_fetch_pages').id
                    redirect_url = f"/web#id={wizard.id}&view_type=form&model=wizard.fetch.pages&action={action_id}"
                    print(f"Redirecting to wizard: {redirect_url}")
                    print("=" * 80)
                    return request.redirect(redirect_url)
                else:
                    print("ERROR: No Facebook pages found for this account")
            else:
                print(f"ERROR: Error getting Facebook access token: {token}")

        print("=" * 80)
        return request.redirect(
            "/web#action=social_media_base.social_media_act_window_kanban"
        )
