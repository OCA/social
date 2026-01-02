# Copyright 2025 Kencove (https://www.kencove.com/)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class SocialComment(models.Model):
    """Comment Moderation System - Generic across all social platforms"""

    _name = "social.comment"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _description = "Social Media Comment"
    _order = "created_time desc"
    _rec_name = "message"

    # Core fields
    post_id = fields.Many2one(
        "social.post",
        string="Post",
        required=True,
        ondelete="cascade",
        index=True,
    )
    comment_id = fields.Char(
        string="Comment ID",
        required=True,
        index=True,
        help="External comment ID from the social platform",
    )
    parent_id = fields.Many2one(
        "social.comment",
        string="Parent Comment",
        ondelete="cascade",
        help="For nested replies",
    )
    reply_ids = fields.One2many(
        "social.comment",
        "parent_id",
        string="Replies",
    )

    # Content
    message = fields.Text(required=True)
    author_name = fields.Char()
    author_id = fields.Char(string="Author ID", help="External author ID")
    author_avatar = fields.Char(string="Author Avatar URL")
    attachment_ids = fields.Many2many(
        "ir.attachment",
        "social_comment_attachment_rel",
        "comment_id",
        "attachment_id",
        string="Attachments",
        help="Files attached to this comment",
    )

    # Timestamps
    created_time = fields.Datetime(string="Created At", required=True)
    last_sync_at = fields.Datetime(string="Last Synced At")

    # Status
    is_replied = fields.Boolean(string="Replied", default=False)
    is_hidden = fields.Boolean(string="Hidden", default=False)
    reply_count = fields.Integer(compute="_compute_reply_count", store=True)

    # Moderation
    sentiment = fields.Selection(
        [
            ("positive", "Positive"),
            ("neutral", "Neutral"),
            ("negative", "Negative"),
        ],
        help="Auto-detected or manual sentiment",
    )
    requires_action = fields.Boolean(default=False)
    assigned_to = fields.Many2one("res.users")
    notes = fields.Text(string="Internal Notes")

    # mail.activity.mixin - Override to add groups for cleaner prefetch
    activity_ids = fields.One2many(groups="base.group_user")
    activity_state = fields.Selection(groups="base.group_user")
    activity_user_id = fields.Many2one(groups="base.group_user")
    activity_type_id = fields.Many2one(groups="base.group_user")
    activity_type_icon = fields.Char(groups="base.group_user")
    activity_date_deadline = fields.Date(groups="base.group_user")
    my_activity_date_deadline = fields.Date(groups="base.group_user")
    activity_summary = fields.Char(groups="base.group_user")
    activity_exception_decoration = fields.Selection(groups="base.group_user")
    activity_exception_icon = fields.Char(groups="base.group_user")

    _comment_id_unique = models.Constraint(
        "unique(comment_id)",
        "This comment has already been synced!",
    )

    @api.depends("reply_ids")
    def _compute_reply_count(self):
        for record in self:
            record.reply_count = len(record.reply_ids)

    def action_reply(self):
        """Open wizard to reply to comment"""
        self.ensure_one()
        return {
            "name": "Reply to Comment",
            "type": "ir.actions.act_window",
            "res_model": "wizard.comment.reply",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_comment_id": self.id,
                "default_post_id": self.post_id.id,
            },
        }

    def action_hide(self):
        """Hide comment on social platform - platform-specific implementation"""
        self.ensure_one()
        # Delegate to platform-specific account implementation
        for account in self.post_id.account_ids:
            if hasattr(account, "_hide_comment"):
                success = account._hide_comment(self.comment_id)
                if success:
                    self.is_hidden = True
                    return True
        return True

    def action_mark_replied(self):
        """Mark comment as replied"""
        self.write({"is_replied": True})

    def action_assign_to_me(self):
        """Assign comment to current user"""
        self.write({"assigned_to": self.env.user.id})
