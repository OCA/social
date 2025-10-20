# Copyright 2025 Binhex <https://www.binhex.cloud>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import json

from odoo import api, fields, models


class SocialLeadForm(models.Model):
    """Feature #5: Facebook Lead Form metadata and configuration"""

    _name = "social.lead.form"
    _description = "Facebook Lead Form"
    _order = "created_time desc"

    name = fields.Char(string="Form Name", required=True)
    fb_form_id = fields.Char(string="Facebook Form ID", required=True, index=True)
    account_id = fields.Many2one(
        "social.account",
        string="Facebook Account",
        required=True,
        ondelete="cascade",
    )
    post_id = fields.Many2one(
        "social.post",
        string="Associated Ad",
        help="The Facebook ad using this lead form",
        ondelete="set null",
    )

    # Form metadata
    status = fields.Selection(
        [("active", "Active"), ("archived", "Archived"), ("deleted", "Deleted")],
        string="Status",
        default="active",
    )
    created_time = fields.Datetime(string="Created Time")
    questions = fields.Text(
        string="Form Questions (JSON)",
        help="JSON array of form questions and field types",
    )
    privacy_policy_url = fields.Char(string="Privacy Policy URL")
    locale = fields.Char(string="Locale", default="en_US")

    # Sync status
    last_sync_at = fields.Datetime(string="Last Sync")
    leads_count = fields.Integer(
        string="Total Leads",
        compute="_compute_leads_count",
        store=False,
    )

    # Field mapping configuration
    field_mapping_ids = fields.One2many(
        "social.lead.field.mapping",
        "lead_form_id",
        string="Field Mappings",
    )

    # Webhook configuration
    webhook_enabled = fields.Boolean(
        string="Webhook Enabled",
        default=False,
        help="Enable real-time webhook notifications for new leads",
    )

    _sql_constraints = [
        ("fb_form_id_unique", "unique(fb_form_id)", "This lead form is already synced!")
    ]

    @api.depends("fb_form_id")
    def _compute_leads_count(self):
        """Count total leads received for this form"""
        for record in self:
            record.leads_count = self.env["social.lead"].search_count([
                ("lead_form_id", "=", record.id)
            ])

    def action_sync_leads(self):
        """Manually sync leads from Facebook for this form"""
        self.ensure_one()
        print(f"Manually syncing leads for form: {self.name}")

        if not self.account_id.page_access_token:
            print(f"WARNING: No access token for account {self.account_id.name}")
            return

        # Fetch leads from Facebook
        endpoint = f"{self.fb_form_id}/leads"
        params = {
            "access_token": self.account_id.page_access_token,
            "limit": 100,
        }

        # Incremental sync
        if self.last_sync_at:
            params["filtering"] = json.dumps([{
                "field": "time_created",
                "operator": "GREATER_THAN",
                "value": int(self.last_sync_at.timestamp()),
            }])

        response = self.account_id._request_facebook(endpoint=endpoint, params=params)

        if isinstance(response, dict) and response.get("data"):
            leads_data = response.get("data", [])
            print(f"Retrieved {len(leads_data)} leads from Facebook")

            created_count = 0
            for lead_data in leads_data:
                try:
                    self._process_lead_data(lead_data)
                    created_count += 1
                except Exception as e:
                    print(f"ERROR: Error processing lead {lead_data.get('id')}: {str(e)}")
                    continue

            self.last_sync_at = fields.Datetime.now()

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
            print(f"WARNING: No leads data in response: {response}")

    def action_view_leads(self):
        """Open list view of leads for this form"""
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": "Leads",
            "res_model": "social.lead",
            "view_mode": "list,form",
            "domain": [("lead_form_id", "=", self.id)],
            "context": {"default_lead_form_id": self.id},
        }

    def _process_lead_data(self, lead_data):
        """Process and store Facebook lead data

        Args:
            lead_data: Dict containing lead information from Facebook API
                {
                    "id": "lead_id",
                    "created_time": "2025-01-15T10:30:00+0000",
                    "field_data": [
                        {"name": "email", "values": ["john@example.com"]},
                        {"name": "full_name", "values": ["John Doe"]},
                        ...
                    ]
                }
        """
        fb_lead_id = lead_data.get("id")

        # Check if lead already exists
        existing_lead = self.env["social.lead"].search([
            ("fb_lead_id", "=", fb_lead_id)
        ], limit=1)

        if existing_lead:
            print(f"Lead {fb_lead_id} already exists, skipping")
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
    """Feature #5: Facebook Lead Data"""

    _name = "social.lead"
    _description = "Facebook Lead"
    _order = "created_time desc"

    lead_form_id = fields.Many2one(
        "social.lead.form",
        string="Lead Form",
        required=True,
        ondelete="cascade",
    )
    fb_lead_id = fields.Char(string="Facebook Lead ID", required=True, index=True)
    created_time = fields.Datetime(string="Created Time", required=True)

    # Extracted common fields
    name = fields.Char(string="Name")
    email = fields.Char(string="Email")
    phone = fields.Char(string="Phone")

    # Raw data from Facebook
    field_data_json = fields.Text(
        string="Field Data (JSON)",
        help="Raw field data from Facebook as JSON",
    )

    # Link to CRM
    crm_lead_id = fields.Many2one(
        "crm.lead",
        string="CRM Lead",
        help="Linked Odoo CRM Lead/Opportunity",
        ondelete="set null",
    )

    status = fields.Selection(
        [
            ("new", "New"),
            ("processed", "Processed"),
            ("converted", "Converted to CRM"),
            ("error", "Error"),
        ],
        string="Status",
        default="new",
    )

    error_message = fields.Text(string="Error Message")

    _sql_constraints = [
        ("fb_lead_id_unique", "unique(fb_lead_id)", "This lead is already synced!")
    ]

    def action_create_crm_lead(self):
        """Convert Facebook lead to CRM lead using field mappings"""
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
                "description": f"Source: Facebook Lead Form\nForm: {self.lead_form_id.name}\nLead ID: {self.fb_lead_id}",
                "source_id": self.env.ref("utm.utm_source_facebook", raise_if_not_found=False).id,
                "fb_lead_id": self.fb_lead_id,
            }

            # Apply custom field mappings
            for mapping in self.lead_form_id.field_mapping_ids:
                fb_field_value = field_dict.get(mapping.fb_field_name)
                if fb_field_value:
                    crm_values[mapping.crm_field_name] = fb_field_value

            # Create CRM lead
            crm_lead = self.env["crm.lead"].create(crm_values)

            # Update social lead
            self.write({
                "crm_lead_id": crm_lead.id,
                "status": "converted",
            })

            print(f"Created CRM lead {crm_lead.id} from Facebook lead {self.fb_lead_id}")

            return {
                "type": "ir.actions.act_window",
                "res_model": "crm.lead",
                "res_id": crm_lead.id,
                "view_mode": "form",
                "target": "current",
            }

        except Exception as e:
            print(f"ERROR: Error creating CRM lead: {str(e)}")
            self.write({
                "status": "error",
                "error_message": str(e),
            })
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
    """Feature #5: Field mapping configuration for Facebook leads to CRM"""

    _name = "social.lead.field.mapping"
    _description = "Facebook Lead Field Mapping"

    lead_form_id = fields.Many2one(
        "social.lead.form",
        string="Lead Form",
        required=True,
        ondelete="cascade",
    )
    fb_field_name = fields.Char(
        string="Facebook Field",
        required=True,
        help="Field name from Facebook lead form (e.g., 'email', 'full_name', 'company_name')",
    )
    crm_field_name = fields.Selection(
        [
            ("name", "Lead Name"),
            ("contact_name", "Contact Name"),
            ("email_from", "Email"),
            ("phone", "Phone"),
            ("mobile", "Mobile"),
            ("function", "Job Position"),
            ("website", "Website"),
            ("street", "Street"),
            ("street2", "Street 2"),
            ("city", "City"),
            ("zip", "Zip"),
            ("country_id", "Country"),
            ("state_id", "State"),
            ("description", "Notes"),
        ],
        string="CRM Field",
        required=True,
        help="Target field in Odoo CRM lead",
    )

    _sql_constraints = [
        (
            "unique_fb_field_per_form",
            "unique(lead_form_id, fb_field_name)",
            "Each Facebook field can only be mapped once per form!"
        )
    ]
