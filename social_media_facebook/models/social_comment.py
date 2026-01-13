# Copyright 2025 Kencove (https://www.kencove.com/)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class SocialComment(models.Model):
    _inherit = "social.comment"

    @api.model_create_multi
    def create(self, vals_list):
        """Override create to trigger comment count recomputation"""
        comments = super().create(vals_list)
        # Trigger recomputation of comment_count for affected posts
        post_ids = comments.mapped("post_id")
        if post_ids:
            post_accounts = self.env["social.post.account"].search(
                [("post_id", "in", post_ids.ids), ("media_type", "=", "facebook")]
            )
            if post_accounts:
                post_accounts._compute_facebook_comment_count()
        return comments

    def write(self, vals):
        """Override write to trigger comment count recomputation if needed"""
        result = super().write(vals)
        # If post_id changed, recompute for both old and new posts
        if "post_id" in vals:
            post_accounts = self.env["social.post.account"].search(
                [
                    ("post_id", "in", self.mapped("post_id").ids),
                    ("media_type", "=", "facebook"),
                ]
            )
            if post_accounts:
                post_accounts._compute_facebook_comment_count()
        return result

    def unlink(self):
        """Override unlink to trigger comment count recomputation"""
        # Get affected posts before unlinking
        post_ids = self.mapped("post_id")
        result = super().unlink()
        if post_ids:
            post_accounts = self.env["social.post.account"].search(
                [("post_id", "in", post_ids.ids), ("media_type", "=", "facebook")]
            )
            if post_accounts:
                post_accounts._compute_facebook_comment_count()
        return result

    def action_reply(self, message=None):
        """
        Reply to a Facebook comment.

        If message is provided, post the reply directly to Facebook.
        Otherwise, open the reply wizard (default behavior).

        Args:
            message (str, optional): The reply message to post

        Returns:
            dict: Action result or success status
        """
        self.ensure_one()

        # If no message provided, open wizard (default behavior)
        if not message:
            return super().action_reply()

        fb_account = next(
            (
                acc
                for acc in self.post_id.account_ids
                if acc.media_type == "facebook"
                and callable(getattr(acc, "_reply_to_facebook_comment", None))
            ),
            None,
        )
        if not fb_account:
            return {
                "success": False,
                "message": "No Facebook account found for this post",
            }

        result = fb_account._reply_to_facebook_comment(self.comment_id, message)
        fb_comment_id = result.get("id") if isinstance(result, dict) else None
        if not fb_comment_id:
            return {"success": False, "message": "Failed to post reply to Facebook"}

        self.is_replied = True

        reply_comment = self.env["social.comment"].create(
            {
                "post_id": self.post_id.id,
                "comment_id": fb_comment_id,
                "parent_id": self.id,
                "message": message,
                "author_name": self.env.user.name,
                "author_id": str(fb_account.page_id or ""),
                "created_time": fields.Datetime.now(),
                "is_replied": False,
                "is_hidden": False,
            }
        )

        return {
            "success": True,
            "message": "Reply posted successfully",
            "comment_id": fb_comment_id,
            "reply_record_id": reply_comment.id,
        }

    def action_hide(self):
        """
        Hide a Facebook comment.

        Returns:
            dict: Success status and message for UI notification
        """
        self.ensure_one()

        fb_account = next(
            (
                acc
                for acc in self.post_id.account_ids
                if acc.media_type == "facebook"
                and callable(getattr(acc, "_hide_facebook_comment", None))
            ),
            None,
        )
        if not fb_account:
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": "Error",
                    "message": "No Facebook account found for this post",
                    "type": "warning",
                    "sticky": False,
                },
            }

        result = fb_account._hide_facebook_comment(self.comment_id)

        if not isinstance(result, dict):
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": "Failed to Hide Comment",
                    "message": "Failed to hide comment on Facebook",
                    "type": "danger",
                    "sticky": True,
                },
            }

        if result.get("success"):
            self.is_hidden = True
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": "Success",
                    "message": result.get("message", "Comment hidden successfully"),
                    "type": "success",
                    "sticky": False,
                },
            }

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": (
                    f"Failed to Hide Comment ({result.get('error_code', 'UNKNOWN')})"
                ),
                "message": result.get("message", "Failed to hide comment on Facebook"),
                "type": "danger",
                "sticky": True,
            },
        }
