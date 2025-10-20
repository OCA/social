# Copyright 2025 Binhex <https://www.binhex.cloud>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import hashlib
import hmac
import json

from odoo import http
from odoo.http import request


class FacebookWebhookController(http.Controller):
    """Feature #5: Webhook endpoint for Facebook Lead Ads"""

    @http.route(
        "/facebook/webhook/leads",
        type="http",
        auth="none",
        methods=["GET"],
        csrf=False,
    )
    def facebook_webhook_verify(self, **kwargs):
        """Verify webhook subscription

        Facebook will send a GET request with:
        - hub.mode=subscribe
        - hub.challenge=<random_string>
        - hub.verify_token=<your_verify_token>

        We must respond with hub.challenge if verify_token matches
        """
        hub_mode = kwargs.get("hub.mode")
        hub_challenge = kwargs.get("hub.challenge")
        hub_verify_token = kwargs.get("hub.verify_token")

        # Get verify token from system parameters
        verify_token = request.env["ir.config_parameter"].sudo().get_param(
            "social_media_facebook.webhook_verify_token", "odoo_facebook_webhook"
        )

        print("Webhook verification request received")
        print(f"Mode: {hub_mode}, Token: {hub_verify_token}")

        if hub_mode == "subscribe" and hub_verify_token == verify_token:
            print("Webhook verification successful, returning challenge")
            return hub_challenge
        else:
            print("WARNING: Webhook verification failed!")
            return "Verification failed", 403

    @http.route(
        "/facebook/webhook/leads",
        type="http",
        auth="none",
        methods=["POST"],
        csrf=False,
    )
    def facebook_webhook_receive(self, **kwargs):
        """Receive lead webhooks from Facebook

        Facebook sends POST requests with structure:
        {
            "object": "page",
            "entry": [
                {
                    "id": "<page_id>",
                    "time": 1234567890,
                    "changes": [
                        {
                            "field": "leadgen",
                            "value": {
                                "leadgen_id": "<lead_id>",
                                "form_id": "<form_id>",
                                "page_id": "<page_id>",
                                "adgroup_id": "<ad_id>",
                                "created_time": 1234567890
                            }
                        }
                    ]
                }
            ]
        }
        """
        try:
            # Verify signature
            signature = request.httprequest.headers.get("X-Hub-Signature-256", "")
            if not self._verify_signature(request.httprequest.data, signature):
                print("WARNING: Invalid webhook signature!")
                return "Invalid signature", 403

            # Parse webhook data
            data = json.loads(request.httprequest.data)
            print(f"Received webhook data: {json.dumps(data, indent=2)}")

            if data.get("object") != "page":
                print("WARNING: Webhook object is not 'page', ignoring")
                return "OK"

            # Process each entry
            for entry in data.get("entry", []):
                for change in entry.get("changes", []):
                    if change.get("field") == "leadgen":
                        self._process_leadgen_webhook(change.get("value", {}))

            return "OK"

        except Exception as e:
            print(f"ERROR: Error processing webhook: {str(e)}")
            return "Error", 500

    def _verify_signature(self, payload, signature_header):
        """Verify webhook signature using app secret

        Args:
            payload: Raw request body bytes
            signature_header: X-Hub-Signature-256 header value

        Returns:
            bool: True if signature is valid
        """
        if not signature_header.startswith("sha256="):
            return False

        # Get app secret from system parameters
        app_secret = request.env["ir.config_parameter"].sudo().get_param(
            "social_media_facebook.app_secret"
        )

        if not app_secret:
            print("WARNING: App secret not configured, skipping signature verification")
            return True  # Allow webhooks if secret not configured

        # Compute expected signature
        expected_signature = hmac.new(
            app_secret.encode(),
            payload,
            hashlib.sha256
        ).hexdigest()

        # Compare signatures
        received_signature = signature_header.replace("sha256=", "")

        return hmac.compare_digest(expected_signature, received_signature)

    def _process_leadgen_webhook(self, leadgen_data):
        """Process leadgen webhook notification

        Args:
            leadgen_data: Dict with lead information
                {
                    "leadgen_id": "<lead_id>",
                    "form_id": "<form_id>",
                    "page_id": "<page_id>",
                    "adgroup_id": "<ad_id>",
                    "created_time": 1234567890
                }
        """
        print(f"Processing leadgen webhook: {leadgen_data}")

        lead_id = leadgen_data.get("leadgen_id")
        form_id = leadgen_data.get("form_id")
        page_id = leadgen_data.get("page_id")

        if not all([lead_id, form_id, page_id]):
            print("WARNING: Missing required fields in leadgen data")
            return

        # Find the lead form in Odoo
        LeadForm = request.env["social.lead.form"].sudo()
        lead_form = LeadForm.search([("fb_form_id", "=", form_id)], limit=1)

        if not lead_form:
            print(f"WARNING: Lead form {form_id} not found in Odoo, skipping")
            return

        # Fetch full lead data from Facebook
        try:
            account = lead_form.account_id
            if not account or not account.page_access_token:
                print(f"WARNING: No access token for lead form {form_id}")
                return

            # Fetch lead details from Facebook API
            endpoint = f"{lead_id}"
            params = {
                "access_token": account.page_access_token,
                "fields": "id,created_time,field_data",
            }

            response = account._request_facebook(endpoint=endpoint, params=params)

            if isinstance(response, dict):
                # Process the lead data
                lead_form._process_lead_data(response)
                print(f"Successfully processed lead {lead_id}")
            else:
                print(f"ERROR: Failed to fetch lead {lead_id} from Facebook: {response}")

        except Exception as e:
            print(f"ERROR: Error fetching lead from Facebook: {str(e)}")
