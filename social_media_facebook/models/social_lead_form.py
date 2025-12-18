# Copyright 2025 Kencove (https://www.kencove.com/)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import json
import logging

from odoo import fields, models

_logger = logging.getLogger(__name__)


class SocialLeadForm(models.Model):
    """Facebook-specific Lead Form extension"""

    _inherit = "social.lead.form"

    # Facebook-specific fields
    fb_form_id = fields.Char(
        string="Facebook Form ID",
        index=True,
        help="Unique Facebook form identifier",
    )

    _sql_constraints = [
        (
            "fb_form_id_unique",
            "unique(fb_form_id)",
            "This Facebook lead form is already synced!",
        )
    ]

    def action_sync_leads(self):
        """Override: Sync leads from Facebook for this form"""
        # Only process Facebook forms
        facebook_forms = self.filtered(lambda f: f.platform == "facebook")
        if not facebook_forms:
            return super().action_sync_leads()

        results = []
        for form in facebook_forms:
            result = form._sync_facebook_leads()
            if result:
                results.append(result)

        # Call super for non-Facebook forms
        other_forms = self - facebook_forms
        if other_forms:
            super(SocialLeadForm, other_forms).action_sync_leads()

        return results[0] if results else {}

    def _sync_facebook_leads(self):
        """Facebook-specific lead sync implementation"""
        self.ensure_one()
        _logger.debug(f"Manually syncing leads for Facebook form: {self.name}")

        if not self.account_id.page_access_token:
            _logger.warning(f"No access token for account {self.account_id.name}")
            return

        # Fetch leads from Facebook
        endpoint = f"{self.fb_form_id}/leads"
        params = {
            "access_token": self.account_id.page_access_token,
            "limit": 100,
        }

        # Incremental sync
        if self.last_sync_at:
            params["filtering"] = json.dumps(
                [
                    {
                        "field": "time_created",
                        "operator": "GREATER_THAN",
                        "value": int(self.last_sync_at.timestamp()),
                    }
                ]
            )

        response = self.account_id._request_facebook(endpoint=endpoint, params=params)

        if isinstance(response, dict) and response.get("data"):
            leads_data = response.get("data", [])
            _logger.debug(f"Retrieved {len(leads_data)} leads from Facebook")

            created_count = 0
            failed_count = 0
            for lead_data in leads_data:
                try:
                    self._process_facebook_lead_data(lead_data)
                    created_count += 1
                except Exception as e:
                    _logger.error(
                        f"Error processing lead {lead_data.get('id')}: {str(e)}"
                    )
                    failed_count += 1
                    continue

            # Only update last_sync_at if all leads processed successfully
            if failed_count == 0:
                self.last_sync_at = fields.Datetime.now()
            elif created_count > 0:
                _logger.warning(
                    f"{failed_count} leads failed to process, last_sync_at not updated"
                )

            # Return notification with results
            if failed_count > 0:
                return {
                    "type": "ir.actions.client",
                    "tag": "display_notification",
                    "params": {
                        "title": "Leads Sync Partial Success",
                        "message": (
                            f"Synced {created_count} leads, "
                            f"{failed_count} failed. Check logs for details."
                        ),
                        "type": "warning",
                        "sticky": True,
                    },
                }
            else:
                return {
                    "type": "ir.actions.client",
                    "tag": "display_notification",
                    "params": {
                        "title": "Leads Synced",
                        "message": f"Successfully synced {created_count} new leads",
                        "type": "success",
                        "sticky": False,
                    },
                }
        else:
            _logger.warning(f"No leads data in response: {response}")

    def _process_facebook_lead_data(self, lead_data):
        """Process and store Facebook lead data"""
        fb_lead_id = lead_data.get("id")

        # Check if lead already exists
        existing_lead = self.env["social.lead"].search(
            [("fb_lead_id", "=", fb_lead_id)], limit=1
        )

        if existing_lead:
            _logger.debug(f"Lead {fb_lead_id} already exists, skipping")
            return existing_lead

        # Parse field data
        field_data = lead_data.get("field_data", [])
        field_data_json = json.dumps(field_data)

        # Extract common fields
        email = None
        name = None
        phone = None

        for field in field_data:
            field_name = field.get("name", "").lower()
            values = field.get("values", [])
            if not values:
                continue

            if field_name == "email":
                email = values[0]
            elif field_name in ["full_name", "name"]:
                name = values[0]
            elif field_name in ["phone_number", "phone"]:
                phone = values[0]

        # Create social.lead record
        lead_vals = {
            "lead_form_id": self.id,
            "fb_lead_id": fb_lead_id,
            "created_time": lead_data.get("created_time"),
            "field_data_json": field_data_json,
            "email": email,
            "name": name,
            "phone": phone,
            "status": "new",
        }

        social_lead = self.env["social.lead"].create(lead_vals)

        # Auto-create CRM lead if field mapping is configured
        if self.field_mapping_ids:
            social_lead.action_create_crm_lead()

        return social_lead


class SocialLead(models.Model):
    """Facebook-specific Lead extension"""

    _inherit = "social.lead"

    # Facebook-specific field
    fb_lead_id = fields.Char(
        string="Facebook Lead ID",
        index=True,
        help="Unique Facebook lead identifier",
    )

    _sql_constraints = [
        (
            "fb_lead_id_unique",
            "unique(fb_lead_id)",
            "This Facebook lead is already synced!",
        )
    ]

    def action_create_crm_lead(self):
        """Override: Add Facebook-specific logic for CRM lead creation"""
        # Filter Facebook leads
        facebook_leads = self.filtered(lambda lead: lead.platform == "facebook")

        if facebook_leads:
            for lead in facebook_leads:
                result = lead._create_facebook_crm_lead()
                if result:
                    return result

        # Call super for non-Facebook leads
        other_leads = self - facebook_leads
        if other_leads:
            return super(SocialLead, other_leads).action_create_crm_lead()

    def _create_facebook_crm_lead(self):
        """Facebook-specific CRM lead creation"""
        self.ensure_one()

        if self.crm_lead_id:
            return {
                "type": "ir.actions.act_window",
                "res_model": "crm.lead",
                "res_id": self.crm_lead_id.id,
                "view_mode": "form",
                "target": "current",
            }

        try:
            # Parse field data
            field_data = json.loads(self.field_data_json or "[]")
            field_dict = {}
            for field in field_data:
                field_name = field.get("name")
                values = field.get("values", [])
                if values:
                    field_dict[field_name] = values[0] if len(values) == 1 else values

            # Apply field mappings
            crm_values = {
                "name": self.name or "Facebook Lead",
                "email_from": self.email,
                "phone": self.phone,
                "description": (
                    f"Source: Facebook Lead Form"
                    f"\nForm: {self.lead_form_id.name}\nLead ID: {self.fb_lead_id}",
                ),
                "source_id": self.env.ref(
                    "utm.utm_source_facebook", raise_if_not_found=False
                ).id,
            }

            # Apply custom field mappings
            for mapping in self.lead_form_id.field_mapping_ids:
                fb_field_value = field_dict.get(mapping.platform_field_name)
                if fb_field_value:
                    crm_values[mapping.crm_field_name] = fb_field_value

            # Create CRM lead
            crm_lead = self.env["crm.lead"].create(crm_values)

            # Update social lead
            self.write(
                {
                    "crm_lead_id": crm_lead.id,
                    "status": "converted",
                }
            )

            _logger.debug(
                f"Created CRM lead {crm_lead.id} from Facebook lead {self.fb_lead_id}"
            )

            return {
                "type": "ir.actions.act_window",
                "res_model": "crm.lead",
                "res_id": crm_lead.id,
                "view_mode": "form",
                "target": "current",
            }

        except Exception as e:
            _logger.error(f"Error creating CRM lead: {str(e)}")
            self.write(
                {
                    "status": "error",
                    "error_message": str(e),
                }
            )
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": "Error",
                    "message": f"Failed to create CRM lead: {str(e)}",
                    "type": "danger",
                    "sticky": True,
                },
            }


class SocialLeadFieldMapping(models.Model):
    """Inherit to ensure compatibility with renamed field"""

    _inherit = "social.lead.field.mapping"

    # Keep fb_field_name as alias for backward compatibility
    fb_field_name = fields.Char(
        related="platform_field_name",
        string="Facebook Field (deprecated)",
        readonly=False,
        help="Deprecated: Use platform_field_name instead",
    )
