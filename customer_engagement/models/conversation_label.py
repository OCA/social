"""Support Conversation Label Model."""

from odoo import fields, models


class ConversationLabel(models.Model):
    """Labels/tags for categorizing support conversations."""

    _name = "support.conversation.label"
    _description = "Conversation Label"
    _order = "sequence, name"

    name = fields.Char(
        required=True,
        translate=True,
    )
    sequence = fields.Integer(
        default=10,
    )
    color = fields.Integer(
        string="Color Index",
        default=0,
        help="Color index for kanban display (0-11)",
    )
    description = fields.Text(
        translate=True,
    )
    active = fields.Boolean(
        default=True,
    )
    conversation_count = fields.Integer(
        string="Conversations",
        compute="_compute_conversation_count",
    )

    def _compute_conversation_count(self):
        """Count conversations using this label."""
        for label in self:
            label.conversation_count = self.env["support.conversation"].search_count(
                [("label_ids", "in", label.id)]
            )
