"""Support Folder Model."""

from odoo import api, fields, models


class SupportFolder(models.Model):
    """Custom folders for organizing conversations."""

    _name = "support.folder"
    _description = "Support Folder"
    _order = "sequence, name"

    name = fields.Char(
        required=True,
        translate=True,
    )
    sequence = fields.Integer(
        default=10,
    )
    code = fields.Char(
        help="Internal code for programmatic access",
    )
    icon = fields.Char(
        default="fa-folder",
        help="Font Awesome icon class (e.g., fa-folder, fa-star)",
    )
    color = fields.Integer(
        string="Color Index",
        default=0,
    )
    description = fields.Text(
        translate=True,
    )
    active = fields.Boolean(
        default=True,
    )
    is_system = fields.Boolean(
        string="System Folder",
        default=False,
        help="System folders cannot be deleted",
    )
    folder_type = fields.Selection(
        selection=[
            ("static", "Static (Manual)"),
            ("smart", "Smart (Auto-filter)"),
        ],
        default="static",
        required=True,
    )
    domain = fields.Char(
        string="Filter Domain",
        help="Domain filter for smart folders (JSON format)",
    )
    user_id = fields.Many2one(
        comodel_name="res.users",
        string="Owner",
        help="If set, folder is private to this user",
    )
    conversation_count = fields.Integer(
        string="Conversations",
        compute="_compute_conversation_count",
    )

    @api.depends("folder_type", "domain")
    def _compute_conversation_count(self):
        """Count conversations in this folder."""
        Conversation = self.env["support.conversation"]
        for folder in self:
            if folder.folder_type == "smart" and folder.domain:
                try:
                    import ast

                    domain = ast.literal_eval(folder.domain)
                    folder.conversation_count = Conversation.search_count(domain)
                except (ValueError, SyntaxError):
                    folder.conversation_count = 0
            else:
                folder.conversation_count = Conversation.search_count(
                    [("folder_ids", "in", folder.id)]
                )

    def unlink(self):
        """Prevent deletion of system folders."""
        for folder in self:
            if folder.is_system:
                raise models.ValidationError(
                    f"Cannot delete system folder: {folder.name}"
                )
        return super().unlink()
