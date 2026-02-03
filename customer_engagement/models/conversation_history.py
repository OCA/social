from odoo import fields, models


class ConversationHistory(models.Model):
    _name = "support.conversation.history"
    _description = "Conversation Transition History"
    _order = "create_date desc"

    conversation_id = fields.Many2one(
        comodel_name="support.conversation",
        string="Conversation",
        required=True,
        ondelete="cascade",
        index=True,
    )
    from_stage_id = fields.Many2one(
        comodel_name="support.conversation.stage",
        string="From Stage",
    )
    to_stage_id = fields.Many2one(
        comodel_name="support.conversation.stage",
        string="To Stage",
        required=True,
    )
    user_id = fields.Many2one(
        comodel_name="res.users",
        string="Changed By",
        default=lambda self: self.env.uid,
    )
    notes = fields.Text()
