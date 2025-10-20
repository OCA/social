# Copyright 2025 Binhex <https://www.binhex.cloud>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from datetime import datetime, timedelta

from odoo import _, fields, models


class WizardFacebookSync(models.TransientModel):
    _name = "wizard.facebook.sync"
    _description = "Facebook Content Sync Wizard"

    account_id = fields.Many2one(
        "social.account",
        string="Facebook Account",
        required=True,
        domain=[("media_type", "=", "facebook")],
    )
    from_date = fields.Datetime(
        string="From Date",
        required=True,
        default=lambda self: datetime.now() - timedelta(days=7),
        help="Start date for syncing content",
    )
    to_date = fields.Datetime(
        string="To Date",
        help="End date for syncing content (optional - leave empty for now)",
    )
    sync_posts = fields.Boolean(string="Sync Posts", default=True)
    sync_reels = fields.Boolean(string="Sync Reels/Videos", default=True)
    sync_ads = fields.Boolean(string="Sync Ads", default=False)
    sync_comments = fields.Boolean(string="Sync Comments", default=False)
    sync_leads = fields.Boolean(string="Sync Leads", default=False)

    def action_sync(self):
        """Execute sync with selected date range and types"""
        self.ensure_one()

        if not self.account_id:
            return

        # Build list of sync types
        types = []
        if self.sync_posts:
            types.append('posts')
        if self.sync_reels:
            types.append('reels')
        if self.sync_ads:
            types.append('ads')
        if self.sync_comments:
            types.append('comments')
        if self.sync_leads:
            types.append('leads')

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

        # Execute sync with date range
        try:
            self.account_id._cron_sync_facebook_content(
                from_datetime=self.from_date,
                to_datetime=self.to_date,
                types=types,
            )

            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": _("Sync Complete"),
                    "message": _("Successfully synced content from %s") % self.from_date.strftime("%Y-%m-%d %H:%M"),
                    "type": "success",
                    "sticky": False,
                },
            }
        except Exception as e:
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": _("Sync Failed"),
                    "message": _("Error: %s") % str(e),
                    "type": "danger",
                    "sticky": True,
                },
            }
