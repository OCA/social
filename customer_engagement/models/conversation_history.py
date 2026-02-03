from odoo import fields, models


class ConversationHistory(models.Model):
    _name = "engage.conversation.history"
    _description = "Conversation Transition History"
    _order = "create_date desc"

    conversation_id = fields.Many2one(
        comodel_name="engage.conversation",
        string="Conversation",
        required=True,
        ondelete="cascade",
        index=True,
    )

    # Event type for different kinds of history entries
    event_type = fields.Selection(
        [
            ("stage_change", "Stage Change"),
            ("assignment", "Assignment"),
            ("transfer", "Transfer"),
            ("priority_change", "Priority Change"),
            ("label_add", "Label Added"),
            ("label_remove", "Label Removed"),
            ("sla_pause", "SLA Paused"),
            ("sla_resume", "SLA Resumed"),
            ("integration", "Integration Action"),
            ("csat_sent", "CSAT Sent"),
            ("csat_received", "CSAT Received"),
        ],
        default="stage_change",
        string="Event Type",
    )

    # Stage change fields
    from_stage_id = fields.Many2one(
        comodel_name="engage.conversation.stage",
        string="From Stage",
    )
    to_stage_id = fields.Many2one(
        comodel_name="engage.conversation.stage",
        string="To Stage",
    )

    # Generic value fields for other event types
    old_value = fields.Char(string="Old Value")
    new_value = fields.Char(string="New Value")

    user_id = fields.Many2one(
        comodel_name="res.users",
        string="Changed By",
        default=lambda self: self.env.uid,
    )
    notes = fields.Text()
