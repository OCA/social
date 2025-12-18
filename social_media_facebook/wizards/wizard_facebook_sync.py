# Copyright 2025 Kencove (https://www.kencove.com/)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import logging
from datetime import datetime, timedelta

from odoo import _, api, fields, models

_logger = logging.getLogger(__name__)


class WizardFacebookSync(models.TransientModel):
    _name = "wizard.facebook.sync"
    _description = "Facebook Content Sync Wizard"

    account_ids = fields.Many2many(
        "social.account",
        string="Facebook Accounts",
        required=True,
        domain=[("media_type", "=", "facebook"), ("status", "=", "active")],
        help="Select one or more Facebook accounts to sync",
    )
    from_date = fields.Datetime(
        required=True,
        default=lambda self: datetime.now() - timedelta(days=7),
        help="Start date for syncing content",
    )
    to_date = fields.Datetime(
        help="End date for syncing content (optional - leave empty for now)",
    )
    sync_posts = fields.Boolean(
        default=True,
        help="Syncs all posts including text, images, and videos/reels",
    )
    sync_ads = fields.Boolean(default=False)
    sync_comments = fields.Boolean(
        string="Sync Comments Only",
        default=False,
        help="Syncs only comments (comments are automatically synced with posts/ads)",
    )
    sync_leads = fields.Boolean(default=False)

    @api.model
    def default_get(self, fields_list):
        """Pre-select account(s) from context (active_id or active_ids)"""
        res = super().default_get(fields_list)

        # Get active_id(s) from context
        active_id = self.env.context.get("active_id")
        active_ids = self.env.context.get("active_ids", [])
        active_model = self.env.context.get("active_model")

        # If called from social.account form/tree, pre-select those accounts
        if active_model == "social.account":
            if active_ids:
                # Multiple accounts selected (from list view)
                res["account_ids"] = [(6, 0, active_ids)]
            elif active_id:
                # Single account (from form view)
                res["account_ids"] = [(6, 0, [active_id])]

        return res

    def action_sync(self):
        """Execute sync with selected date range and types"""
        self.ensure_one()

        if not self.account_ids:
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": _("No Account Selected"),
                    "message": _("Please select at least one Facebook account to sync"),
                    "type": "warning",
                    "sticky": False,
                },
            }

        # Build list of sync types
        types = []
        if self.sync_posts:
            types.append("posts")
        if self.sync_ads:
            types.append("ads")
        if self.sync_comments:
            types.append("comments")
        if self.sync_leads:
            types.append("leads")

        if not types:
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": _("No Content Selected"),
                    "message": _("Please select at least one content type to sync"),
                    "type": "warning",
                    "sticky": False,
                },
            }

        # Execute sync with date range for selected accounts
        try:
            self.account_ids._sync_facebook_content(
                from_datetime=self.from_date,
                to_datetime=self.to_date,
                types=types,
            )

            # Show success notification
            account_names = ", ".join(self.account_ids.mapped("name"))
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": _("Sync Complete"),
                    "message": _(
                        "Successfully synced %(count)s account(s): %(accounts)s"
                    )
                    % {
                        "count": len(self.account_ids),
                        "accounts": account_names,
                    },
                    "type": "success",
                    "sticky": False,
                    "next": {"type": "ir.actions.act_window_close"},
                },
            }

        except Exception as e:
            import traceback

            _logger.error(f"Error in sync wizard: {str(e)}")
            _logger.debug(traceback.format_exc())

            # Show error notification
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": _("Sync Failed"),
                    "message": _("Error: %s") % str(e),
                    "type": "danger",
                    "sticky": True,
                    "next": {"type": "ir.actions.act_window_close"},
                },
            }
