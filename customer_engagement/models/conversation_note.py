"""Conversation Note Model."""

from odoo import fields, models


class ConversationNote(models.Model):
    """Private notes attached to conversations (not visible to customers)."""

    _name = "engage.conversation.note"
    _description = "Conversation Note"
    _order = "create_date desc"

    conversation_id = fields.Many2one(
        comodel_name="engage.conversation",
        string="Conversation",
        required=True,
        ondelete="cascade",
        index=True,
    )
    author_id = fields.Many2one(
        comodel_name="res.users",
        string="Author",
        required=True,
        default=lambda self: self.env.user,
        index=True,
    )
    content = fields.Html(
        required=True,
        sanitize=True,
    )
    plain_content = fields.Text(
        compute="_compute_plain_content",
        store=True,
    )
    attachment_ids = fields.Many2many(
        comodel_name="ir.attachment",
        relation="engage_conversation_note_attachment_rel",
        column1="note_id",
        column2="attachment_id",
        string="Attachments",
    )
    mentioned_user_ids = fields.Many2many(
        comodel_name="res.users",
        relation="engage_conversation_note_mention_rel",
        column1="note_id",
        column2="user_id",
        string="Mentioned Users",
        help="Users mentioned in this note using @",
    )
    is_pinned = fields.Boolean(
        string="Pinned",
        default=False,
        help="Pinned notes appear at the top",
    )

    def _compute_plain_content(self):
        """Extract plain text from HTML content."""
        from odoo.tools import html2plaintext

        for note in self:
            if note.content:
                note.plain_content = html2plaintext(note.content)[:500]
            else:
                note.plain_content = ""

    def toggle_pin(self):
        """Toggle the pinned status of a note."""
        for note in self:
            note.is_pinned = not note.is_pinned
