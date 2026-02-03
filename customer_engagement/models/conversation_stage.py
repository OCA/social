from odoo import fields, models


class ConversationStage(models.Model):
    _name = "support.conversation.stage"
    _description = "Conversation Stage"
    _order = "sequence, id"

    name = fields.Char(required=True, translate=True)
    sequence = fields.Integer(default=10)
    code = fields.Selection(
        [
            ("new", "New"),
            ("open", "Open"),
            ("pending", "Pending"),
            ("resolved", "Resolved"),
            ("closed", "Closed"),
        ],
        required=True,
    )

    closed = fields.Boolean(
        help="Conversation is considered closed in this stage",
    )
    fold = fields.Boolean(
        string="Folded in Kanban",
        help="Fold this stage in kanban view when empty",
    )

    mail_template_id = fields.Many2one(
        comodel_name="mail.template",
        string="Email Template",
        domain="[('model', '=', 'support.conversation')]",
        help="Email sent when conversation enters this stage",
    )

    _sql_constraints = [
        ("code_unique", "UNIQUE(code)", "Stage code must be unique"),
    ]
