"""Transfer Wizard for Customer Engagement.

This module provides a wizard for transferring conversations
between agents and teams with proper tracking.
"""

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class EngageTransferWizard(models.TransientModel):
    """Wizard for transferring conversations."""

    _name = "engage.transfer.wizard"
    _description = "Transfer Conversation"

    conversation_id = fields.Many2one(
        "engage.conversation",
        required=True,
        string="Conversation",
        default=lambda self: self.env.context.get("active_id"),
    )
    conversation_uuid = fields.Char(
        related="conversation_id.uuid",
        string="Conversation ID",
    )
    current_user_id = fields.Many2one(
        "res.users",
        related="conversation_id.user_id",
        string="Current Agent",
    )
    current_team_id = fields.Many2one(
        "engage.team",
        related="conversation_id.team_id",
        string="Current Team",
    )

    transfer_type = fields.Selection(
        [
            ("agent", "To Agent"),
            ("team", "To Team"),
        ],
        required=True,
        default="agent",
        string="Transfer To",
    )

    user_id = fields.Many2one(
        "res.users",
        string="Agent",
        domain="[('share', '=', False)]",
    )
    team_id = fields.Many2one(
        "engage.team",
        string="Team",
    )

    reason = fields.Text(
        string="Reason",
        required=True,
        help="Reason for the transfer (will be recorded in history)",
    )

    add_internal_note = fields.Boolean(
        string="Add Internal Note",
        default=True,
        help="Add a note visible to the new assignee",
    )
    note_content = fields.Text(
        string="Note for New Assignee",
        help="Context or instructions for the new assignee",
    )

    keep_in_team = fields.Boolean(
        string="Keep in Current Team",
        default=True,
        help="When transferring to an agent, keep the conversation in the current team",
    )

    @api.onchange("transfer_type")
    def _onchange_transfer_type(self):
        """Clear fields when transfer type changes."""
        if self.transfer_type == "agent":
            self.team_id = False
        else:
            self.user_id = False

    def action_transfer(self):
        """Execute the transfer."""
        self.ensure_one()

        if self.transfer_type == "agent" and not self.user_id:
            raise UserError(_("Please select an agent to transfer to."))
        if self.transfer_type == "team" and not self.team_id:
            raise UserError(_("Please select a team to transfer to."))

        conv = self.conversation_id
        old_user = conv.user_id
        old_team = conv.team_id

        # Prepare values for update
        vals = {}

        if self.transfer_type == "agent":
            if self.user_id == old_user:
                raise UserError(_("Conversation is already assigned to this agent."))
            vals["user_id"] = self.user_id.id
            if not self.keep_in_team:
                # Find team the agent belongs to
                agent_teams = self.env["engage.team"].search(
                    [("member_ids", "in", self.user_id.id)]
                )
                if agent_teams:
                    vals["team_id"] = agent_teams[0].id
        else:
            if self.team_id == old_team:
                raise UserError(_("Conversation is already in this team."))
            vals["team_id"] = self.team_id.id
            vals["user_id"] = False  # Return to team queue

            # Auto-assign if team has auto_assign enabled
            if self.team_id.auto_assign:
                agent = self.team_id.get_available_agent(conversation=conv)
                if agent:
                    vals["user_id"] = agent.id

        # Update conversation
        conv.write(vals)

        # Record in history
        if self.transfer_type == "agent":
            old_value = old_user.name if old_user else _("Unassigned")
            new_value = self.user_id.name
        else:
            old_value = old_team.name if old_team else _("No Team")
            new_value = self.team_id.name

        self.env["engage.conversation.history"].create(
            {
                "conversation_id": conv.id,
                "event_type": "transfer",
                "old_value": old_value,
                "new_value": new_value,
                "notes": self.reason,
            }
        )

        # Add internal note if requested
        if self.add_internal_note and self.note_content:
            self.env["engage.conversation.note"].create(
                {
                    "conversation_id": conv.id,
                    "author_id": self.env.uid,
                    "content": f"<p><strong>Transfer Note:</strong></p><p>{self.note_content}</p>",
                }
            )

        # Notify new assignee
        if vals.get("user_id"):
            new_user = self.env["res.users"].browse(vals["user_id"])
            new_user.notify_info(
                title=_("Conversation Transferred"),
                message=_("Conversation %s has been transferred to you by %s.")
                % (conv.uuid[:8], self.env.user.name),
            )

        return {"type": "ir.actions.act_window_close"}
