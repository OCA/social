# Copyright 2025 Binhex <https://www.binhex.cloud>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, fields, models

CALENDAR_COLOR_BY_STATE = {
    "planned": 2,
    "publishing": 6,
    "published": 10,
    "cancelled": 0,
}
CALENDAR_COLOR_DEFAULT = 4


class SocialPost(models.Model):
    """Places the posts on a calendar view by their relevant date."""

    _inherit = "social.post"

    date_calendar = fields.Datetime(compute="_compute_date_calendar", store=True)
    color = fields.Integer(compute="_compute_color")

    @api.depends("state")
    def _compute_color(self):
        """Map the post state to its calendar color."""
        for post in self:
            post.color = CALENDAR_COLOR_BY_STATE.get(post.state, CALENDAR_COLOR_DEFAULT)

    @api.depends("create_date", "send_post_date", "published_date")
    def _compute_date_calendar(self):
        """Show the post on the date it was published, or the planned one.

        It is a Datetime so the calendar renders it in the time zone of the
        user, as the rest of the dates of the post.
        """
        for post in self:
            post.date_calendar = (
                post.published_date or post.send_post_date or post.create_date
            )
