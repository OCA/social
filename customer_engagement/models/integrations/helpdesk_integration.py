"""Helpdesk Integration for Customer Engagement.

This module provides integration with Odoo's helpdesk module,
allowing agents to view and create tickets from conversations.
"""

from odoo import api, fields, models


class ConversationHelpdeskIntegration(models.Model):
    """Extend conversation with helpdesk integration."""

    _inherit = "engage.conversation"

    # Helpdesk ticket fields (computed to handle missing module)
    helpdesk_ticket_ids = fields.One2many(
        "helpdesk.ticket",
        compute="_compute_helpdesk_tickets",
        string="Support Tickets",
    )
    helpdesk_ticket_count = fields.Integer(
        compute="_compute_helpdesk_tickets",
        string="Ticket Count",
    )
    open_ticket_count = fields.Integer(
        compute="_compute_helpdesk_tickets",
        string="Open Tickets",
    )

    @api.depends("partner_id")
    def _compute_helpdesk_tickets(self):
        """Compute helpdesk tickets for the conversation partner."""
        # Check if helpdesk module is installed
        if "helpdesk.ticket" not in self.env:
            for conv in self:
                conv.helpdesk_ticket_ids = False
                conv.helpdesk_ticket_count = 0
                conv.open_ticket_count = 0
            return

        for conv in self:
            if conv.partner_id:
                tickets = self.env["helpdesk.ticket"].search(
                    [("partner_id", "=", conv.partner_id.id)],
                    order="create_date desc",
                    limit=20,
                )
                conv.helpdesk_ticket_ids = tickets
                conv.helpdesk_ticket_count = len(tickets)
                # Count open tickets (not in closed stage)
                conv.open_ticket_count = len(
                    tickets.filtered(lambda t: not t.stage_id.is_close)
                )
            else:
                conv.helpdesk_ticket_ids = False
                conv.helpdesk_ticket_count = 0
                conv.open_ticket_count = 0

    def action_view_helpdesk_tickets(self):
        """Open helpdesk tickets for this partner."""
        self.ensure_one()
        if "helpdesk.ticket" not in self.env:
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": "Module Not Installed",
                    "message": "The Helpdesk module is not installed.",
                    "type": "warning",
                },
            }

        return {
            "type": "ir.actions.act_window",
            "name": f"Tickets - {self.partner_id.name}",
            "res_model": "helpdesk.ticket",
            "view_mode": "tree,form,kanban",
            "domain": [("partner_id", "=", self.partner_id.id)],
            "context": {
                "default_partner_id": self.partner_id.id,
                "search_default_partner_id": self.partner_id.id,
            },
        }

    def action_create_helpdesk_ticket(self):
        """Create a new helpdesk ticket from this conversation."""
        self.ensure_one()
        if "helpdesk.ticket" not in self.env:
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": "Module Not Installed",
                    "message": "The Helpdesk module is not installed.",
                    "type": "warning",
                },
            }

        # Get conversation summary for ticket description
        description = self._get_conversation_summary()

        return {
            "type": "ir.actions.act_window",
            "name": "New Ticket",
            "res_model": "helpdesk.ticket",
            "view_mode": "form",
            "context": {
                "default_partner_id": self.partner_id.id,
                "default_name": f"From Conversation {self.uuid[:8] if self.uuid else self.id}",
                "default_description": description,
            },
        }

    def action_convert_to_ticket(self):
        """Convert conversation to a helpdesk ticket."""
        self.ensure_one()
        if "helpdesk.ticket" not in self.env:
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": "Module Not Installed",
                    "message": "The Helpdesk module is not installed.",
                    "type": "warning",
                },
            }

        # Get default helpdesk team
        default_team = self.env["helpdesk.team"].search([], limit=1)

        # Create the ticket
        ticket = self.env["helpdesk.ticket"].create(
            {
                "name": self.subject
                or f"Conversation {self.uuid[:8] if self.uuid else self.id}",
                "partner_id": self.partner_id.id,
                "description": self._get_conversation_summary(),
                "team_id": default_team.id if default_team else False,
            }
        )

        # Log in conversation history
        self.env["engage.conversation.history"].create(
            {
                "conversation_id": self.id,
                "event_type": "integration",
                "notes": f"Converted to ticket {ticket.name}",
            }
        )

        return {
            "type": "ir.actions.act_window",
            "name": "Ticket",
            "res_model": "helpdesk.ticket",
            "res_id": ticket.id,
            "view_mode": "form",
        }

    def _get_conversation_summary(self):
        """Get a summary of the conversation for ticket description."""
        messages = self.message_ids.filtered(
            lambda m: m.message_type in ("comment", "email")
        ).sorted("date")[:10]

        lines = []
        for msg in messages:
            author = msg.author_id.name if msg.author_id else "Unknown"
            date_str = msg.date.strftime("%Y-%m-%d %H:%M") if msg.date else ""
            body = msg.body or ""
            # Strip HTML tags for plain text
            import re

            body = re.sub("<[^<]+?>", "", body)
            lines.append(f"[{date_str}] {author}: {body[:200]}")

        return "\n".join(lines) if lines else "No messages"
