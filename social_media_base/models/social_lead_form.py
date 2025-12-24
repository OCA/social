# Copyright 2025 Kencove (https://www.kencove.com/)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class SocialLeadForm(models.Model):
    """Generic Social Media Lead Form - works across platforms"""

    _name = "social.lead.form"
    _description = "Social Media Lead Form"
    _order = "created_time desc"

    name = fields.Char(string="Form Name", required=True)
    account_id = fields.Many2one(
        "social.account",
        string="Account",
        required=True,
        ondelete="cascade",
    )
    platform = fields.Selection(
        related="account_id.media_type",
        store=True,
        string="Platform",
        help="Social media platform (facebook, linkedin, etc.)",
    )
    post_id = fields.Many2one(
        "social.post",
        string="Associated Ad",
        help="The ad/post using this lead form",
        ondelete="set null",
    )

    # Form metadata - generic across platforms
    status = fields.Selection(
        [("active", "Active"), ("archived", "Archived"), ("deleted", "Deleted")],
        default="active",
    )
    created_time = fields.Datetime()
    questions = fields.Text(
        string="Form Questions (JSON)",
        help="JSON array of form questions and field types",
    )
    privacy_policy_url = fields.Char(string="Privacy Policy URL")
    locale = fields.Char(default="en_US")

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
        default=False,
        help="Enable real-time webhook notifications for new leads",
    )

    @api.depends("platform")
    def _compute_leads_count(self):
        """Count total leads received for this form"""
        for record in self:
            record.leads_count = self.env["social.lead"].search_count(
                [("lead_form_id", "=", record.id)]
            )

    def action_sync_leads(self):
        """Manually sync leads - platform-specific implementations override this"""
        self.ensure_one()
        # Base implementation - platforms override this method
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": "Sync Not Implemented",
                "message": f"Lead sync not implemented for {self.platform}",
                "type": "warning",
            },
        }

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


class SocialLead(models.Model):
    """Generic Social Media Lead - works across platforms"""

    _name = "social.lead"
    _description = "Social Media Lead"
    _order = "created_time desc"

    lead_form_id = fields.Many2one(
        "social.lead.form",
        string="Lead Form",
        required=True,
        ondelete="cascade",
    )
    platform = fields.Selection(
        related="lead_form_id.platform",
        store=True,
        string="Platform",
    )
    created_time = fields.Datetime(required=True)

    # Extracted common fields (generic across platforms)
    name = fields.Char()
    email = fields.Char()
    phone = fields.Char()

    # Raw data from platform (JSON format)
    field_data_json = fields.Text(
        help="Raw field data from social platform as JSON",
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
        default="new",
    )

    error_message = fields.Text()

    def action_create_crm_lead(self):
        """
        Convert social lead to CRM lead using field
        mappings - platforms may override
        """
        self.ensure_one()

        if self.crm_lead_id:
            return {
                "type": "ir.actions.act_window",
                "res_model": "crm.lead",
                "res_id": self.crm_lead_id.id,
                "view_mode": "form",
                "target": "current",
            }

        # Default CRM lead creation
        import json

        field_data = json.loads(self.field_data_json or "[]")
        field_dict = {}
        for field in field_data:
            field_name = field.get("name")
            values = field.get("values", [])
            if values:
                field_dict[field_name] = values[0] if len(values) == 1 else values

        # Apply field mappings
        crm_values = {
            "name": self.name or f"{self.platform.title()} Lead",
            "email_from": self.email,
            "phone": self.phone,
            "description": (
                f"Source: {self.platform.title()} Lead Form\n"
                f"Form: {self.lead_form_id.name}"
            ),
        }

        # Apply custom field mappings
        for mapping in self.lead_form_id.field_mapping_ids:
            field_value = field_dict.get(mapping.platform_field_name)
            if field_value:
                crm_values[mapping.crm_field_name] = field_value

        try:
            # Create CRM lead
            crm_lead = self.env["crm.lead"].create(crm_values)

            # Update social lead
            self.write(
                {
                    "crm_lead_id": crm_lead.id,
                    "status": "converted",
                }
            )

            return {
                "type": "ir.actions.act_window",
                "res_model": "crm.lead",
                "res_id": crm_lead.id,
                "view_mode": "form",
                "target": "current",
            }

        except Exception as e:
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
    """Field mapping configuration for social leads to CRM"""

    _name = "social.lead.field.mapping"
    _description = "Social Lead Field Mapping"

    lead_form_id = fields.Many2one(
        "social.lead.form",
        string="Lead Form",
        required=True,
        ondelete="cascade",
    )
    platform_field_name = fields.Char(
        string="Platform Field",
        required=True,
        help="Field name from platform (e.g., 'email', 'full_name', 'company_name')",
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
            "unique_platform_field_per_form",
            "unique(lead_form_id, platform_field_name)",
            "Each platform field can only be mapped once per form!",
        )
    ]
