# Copyright 2026 Binhex <https://www.binhex.cloud>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


class LinkTracker(models.Model):
    """Tracked link published on a social media."""

    _inherit = "link.tracker"

    social_post_account_id = fields.Many2one(
        "social.post.account",
        string="Social Media Publication",
        index="btree_not_null",
        ondelete="set null",
        help="Publication the tracked link was published in.",
    )


class LinkTrackerClick(models.Model):
    """Click registered on a link published on a social media."""

    _inherit = "link.tracker.click"

    social_post_account_id = fields.Many2one(
        "social.post.account",
        string="Social Media Publication",
        related="link_id.social_post_account_id",
        store=True,
        index="btree_not_null",
        ondelete="set null",
        help="Publication the clicked link was published in.",
    )
