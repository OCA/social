"""CRM Integration for Customer Engagement.

This module provides integration with Odoo's CRM module,
allowing agents to view and create leads/opportunities from conversations.
"""

from odoo import api, fields, models


class ConversationCRMIntegration(models.Model):
    """Extend conversation with CRM integration."""

    _inherit = "engage.conversation"

    # CRM lead/opportunity fields (computed to handle missing module)
    crm_lead_ids = fields.One2many(
        "crm.lead",
        compute="_compute_crm_leads",
        string="Leads/Opportunities",
    )
    crm_lead_count = fields.Integer(
        compute="_compute_crm_leads",
        string="Lead Count",
    )
    open_opportunity_count = fields.Integer(
        compute="_compute_crm_leads",
        string="Open Opportunities",
    )
    expected_revenue = fields.Monetary(
        compute="_compute_crm_leads",
        string="Expected Revenue",
        currency_field="company_currency_id",
    )

    @api.depends("partner_id")
    def _compute_crm_leads(self):
        """Compute CRM leads for the conversation partner."""
        # Check if CRM module is installed
        if "crm.lead" not in self.env:
            for conv in self:
                conv.crm_lead_ids = False
                conv.crm_lead_count = 0
                conv.open_opportunity_count = 0
                conv.expected_revenue = 0.0
            return

        for conv in self:
            if conv.partner_id:
                leads = self.env["crm.lead"].search(
                    [("partner_id", "=", conv.partner_id.id)],
                    order="create_date desc",
                    limit=20,
                )
                conv.crm_lead_ids = leads
                conv.crm_lead_count = len(leads)
                # Count open opportunities
                open_leads = leads.filtered(
                    lambda l: not l.probability == 0 and l.active
                )
                conv.open_opportunity_count = len(open_leads)
                conv.expected_revenue = sum(open_leads.mapped("expected_revenue"))
            else:
                conv.crm_lead_ids = False
                conv.crm_lead_count = 0
                conv.open_opportunity_count = 0
                conv.expected_revenue = 0.0

    def action_view_crm_leads(self):
        """Open CRM leads/opportunities for this partner."""
        self.ensure_one()
        if "crm.lead" not in self.env:
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": "Module Not Installed",
                    "message": "The CRM module is not installed.",
                    "type": "warning",
                },
            }

        return {
            "type": "ir.actions.act_window",
            "name": f"Opportunities - {self.partner_id.name}",
            "res_model": "crm.lead",
            "view_mode": "tree,kanban,form",
            "domain": [("partner_id", "=", self.partner_id.id)],
            "context": {
                "default_partner_id": self.partner_id.id,
                "search_default_partner_id": self.partner_id.id,
            },
        }

    def action_create_lead(self):
        """Create a new lead from this conversation."""
        self.ensure_one()
        if "crm.lead" not in self.env:
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": "Module Not Installed",
                    "message": "The CRM module is not installed.",
                    "type": "warning",
                },
            }

        return {
            "type": "ir.actions.act_window",
            "name": "New Lead",
            "res_model": "crm.lead",
            "view_mode": "form",
            "context": {
                "default_partner_id": self.partner_id.id,
                "default_name": f"Lead from {self.partner_id.name}",
                "default_type": "lead",
                "default_description": self._get_conversation_context(),
            },
        }

    def action_create_opportunity(self):
        """Create a new opportunity from this conversation."""
        self.ensure_one()
        if "crm.lead" not in self.env:
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": "Module Not Installed",
                    "message": "The CRM module is not installed.",
                    "type": "warning",
                },
            }

        return {
            "type": "ir.actions.act_window",
            "name": "New Opportunity",
            "res_model": "crm.lead",
            "view_mode": "form",
            "context": {
                "default_partner_id": self.partner_id.id,
                "default_name": f"Opportunity from {self.partner_id.name}",
                "default_type": "opportunity",
                "default_description": self._get_conversation_context(),
            },
        }

    def action_convert_to_opportunity(self):
        """Convert conversation to a CRM opportunity."""
        self.ensure_one()
        if "crm.lead" not in self.env:
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": "Module Not Installed",
                    "message": "The CRM module is not installed.",
                    "type": "warning",
                },
            }

        # Get default sales team
        default_team = self.env["crm.team"].search(
            [("use_opportunities", "=", True)], limit=1
        )

        # Create the opportunity
        lead = self.env["crm.lead"].create(
            {
                "name": self.subject
                or f"From Conversation {self.uuid[:8] if self.uuid else self.id}",
                "partner_id": self.partner_id.id,
                "type": "opportunity",
                "description": self._get_conversation_context(),
                "team_id": default_team.id if default_team else False,
                "user_id": self.user_id.id if self.user_id else self.env.uid,
            }
        )

        # Log in conversation history
        self.env["engage.conversation.history"].create(
            {
                "conversation_id": self.id,
                "event_type": "integration",
                "notes": f"Converted to opportunity {lead.name}",
            }
        )

        return {
            "type": "ir.actions.act_window",
            "name": "Opportunity",
            "res_model": "crm.lead",
            "res_id": lead.id,
            "view_mode": "form",
        }

    def _get_conversation_context(self):
        """Get conversation context for CRM lead description."""
        lines = []

        # Add conversation metadata
        lines.append(f"Channel: {self.channel_type or 'N/A'}")
        if self.subject:
            lines.append(f"Subject: {self.subject}")
        lines.append("")

        # Add recent messages
        messages = self.message_ids.filtered(
            lambda m: m.message_type in ("comment", "email")
        ).sorted("date")[:5]

        if messages:
            lines.append("Recent Messages:")
            lines.append("-" * 40)
            for msg in messages:
                author = msg.author_id.name if msg.author_id else "Unknown"
                date_str = msg.date.strftime("%Y-%m-%d %H:%M") if msg.date else ""
                body = msg.body or ""
                # Strip HTML tags
                import re

                body = re.sub("<[^<]+?>", "", body)
                lines.append(f"[{date_str}] {author}:")
                lines.append(body[:300])
                lines.append("")

        return "\n".join(lines)
