# Copyright 2025 Kencove (https://www.kencove.com/)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, models


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

        # Post reply to Facebook
        for account in self.post_id.account_ids:
            if account.media_type == "facebook" and hasattr(
                account, "_reply_to_facebook_comment"
            ):
                result = account._reply_to_facebook_comment(self.comment_id, message)
                if result and isinstance(result, dict) and result.get("id"):
                    # Mark parent as replied
                    self.write({"is_replied": True})

                    # Create the reply comment record in Odoo
                    from datetime import datetime

                    reply_comment = self.env["social.comment"].create(
                        {
                            "post_id": self.post_id.id,
                            "comment_id": result.get("id"),
                            "parent_id": self.id,
                            "message": message,
                            "author_name": self.env.user.name,
                            "author_id": str(account.page_id or ""),
                            "created_time": datetime.now(),
                            "is_replied": False,
                            "is_hidden": False,
                        }
                    )

                    return {
                        "success": True,
                        "message": "Reply posted successfully",
                        "comment_id": result.get("id"),
                        "reply_record_id": reply_comment.id,
                    }
                else:
                    return {
                        "success": False,
                        "message": "Failed to post reply to Facebook",
                    }

        return {
            "success": False,
            "message": "No Facebook account found for this post",
        }

    def action_hide(self):
        """
        Hide a Facebook comment.

        Returns:
            dict: Success status and message for UI notification
        """
        self.ensure_one()

        # Hide comment on Facebook
        for account in self.post_id.account_ids:
            if account.media_type == "facebook" and hasattr(
                account, "_hide_facebook_comment"
            ):
                result = account._hide_facebook_comment(self.comment_id)

                # Check if result is a dict with success status
                if isinstance(result, dict):
                    if result.get("success"):
                        # Mark as hidden in Odoo
                        self.write({"is_hidden": True})
                        return {
                            "type": "ir.actions.client",
                            "tag": "display_notification",
                            "params": {
                                "title": "Success",
                                "message": result.get(
                                    "message", "Comment hidden successfully"
                                ),
                                "type": "success",
                                "sticky": False,
                            },
                        }
                    else:
                        # Return detailed error message from Facebook
                        error_msg = result.get(
                            "message", "Failed to hide comment on Facebook"
                        )
                        error_code = result.get("error_code", "UNKNOWN")
                        return {
                            "type": "ir.actions.client",
                            "tag": "display_notification",
                            "params": {
                                "title": f"Failed to Hide Comment ({error_code})",
                                "message": error_msg,
                                "type": "danger",
                                "sticky": True,
                            },
                        }

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
