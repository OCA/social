# Copyright 2026 Binhex <https://www.binhex.cloud>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, fields, models

CALENDAR_COLOR_BY_STATE = {
    "planned": 2,
    "publishing": 6,
    "partially_published": 3,
    "published": 10,
    "cancelled": 0,
}
CALENDAR_COLOR_DEFAULT = 4


class SocialPost(models.Model):
    """Places the posts on a calendar view by their relevant date."""

    _inherit = "social.post"

    date_calendar = fields.Datetime(compute="_compute_date_calendar", store=True)
    color = fields.Integer(compute="_compute_color")

    @api.model
    def default_get(self, fields_list):
        """Propose the day clicked on the calendar as the schedule date.

        The calendar places the events by ``date_calendar``, which is only a
        read-only summary of the dates of the post, so the date the user
        clicked cannot be written there: it is turned into the date the post
        is really sent, and the post is switched to ``schedule`` because that
        is the only mode where a date can be chosen.

        A day already past is dropped on purpose: *Social Media Base* refuses
        a schedule date behind the clock with a validation error, so keeping
        it would make the form unsavable. Leaving ``send_post_date`` out of
        the defaults lets ``_compute_send_post_date`` propose its usual one
        hour from now.
        """
        res = super().default_get(fields_list)
        date_calendar = fields.Datetime.to_datetime(
            self.env.context.get("default_date_calendar")
        )
        if date_calendar:
            res["send_post"] = "schedule"
            if date_calendar > fields.Datetime.now():
                res["send_post_date"] = date_calendar
        return res

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
