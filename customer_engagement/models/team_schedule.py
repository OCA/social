"""Team Schedule Model for Customer Engagement.

This module provides working hours configuration for engagement teams.
"""

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class EngageTeamSchedule(models.Model):
    """Working hours schedule for engagement teams."""

    _name = "engage.team.schedule"
    _description = "Team Schedule"
    _order = "team_id, day_of_week, start_time"

    team_id = fields.Many2one(
        "engage.team",
        required=True,
        ondelete="cascade",
        string="Team",
        index=True,
    )
    day_of_week = fields.Selection(
        [
            ("0", "Monday"),
            ("1", "Tuesday"),
            ("2", "Wednesday"),
            ("3", "Thursday"),
            ("4", "Friday"),
            ("5", "Saturday"),
            ("6", "Sunday"),
        ],
        required=True,
        string="Day",
    )
    start_time = fields.Float(
        required=True,
        string="Start Time",
        help="Start time in 24h format (e.g., 8.5 = 08:30)",
    )
    end_time = fields.Float(
        required=True,
        string="End Time",
        help="End time in 24h format (e.g., 17.5 = 17:30)",
    )
    name = fields.Char(
        compute="_compute_name",
        store=True,
        string="Name",
    )

    @api.depends("day_of_week", "start_time", "end_time")
    def _compute_name(self):
        """Compute display name."""
        day_names = {
            "0": "Monday",
            "1": "Tuesday",
            "2": "Wednesday",
            "3": "Thursday",
            "4": "Friday",
            "5": "Saturday",
            "6": "Sunday",
        }
        for rec in self:
            day = day_names.get(rec.day_of_week, "")
            start = self._float_to_time_str(rec.start_time)
            end = self._float_to_time_str(rec.end_time)
            rec.name = f"{day} {start} - {end}"

    @staticmethod
    def _float_to_time_str(float_time):
        """Convert float time to HH:MM string."""
        hours = int(float_time)
        minutes = int((float_time - hours) * 60)
        return f"{hours:02d}:{minutes:02d}"

    @api.constrains("start_time", "end_time")
    def _check_times(self):
        """Validate time values."""
        for rec in self:
            if rec.start_time < 0 or rec.start_time >= 24:
                raise ValidationError(_("Start time must be between 0 and 24"))
            if rec.end_time < 0 or rec.end_time >= 24:
                raise ValidationError(_("End time must be between 0 and 24"))
            if rec.start_time >= rec.end_time:
                raise ValidationError(_("Start time must be before end time"))

    @api.constrains("team_id", "day_of_week", "start_time", "end_time")
    def _check_overlap(self):
        """Check for overlapping schedules on the same day."""
        for rec in self:
            overlapping = self.search(
                [
                    ("team_id", "=", rec.team_id.id),
                    ("day_of_week", "=", rec.day_of_week),
                    ("id", "!=", rec.id),
                    "|",
                    "&",
                    ("start_time", "<=", rec.start_time),
                    ("end_time", ">", rec.start_time),
                    "&",
                    ("start_time", "<", rec.end_time),
                    ("end_time", ">=", rec.end_time),
                ]
            )
            if overlapping:
                raise ValidationError(
                    _("Schedule overlaps with existing schedule: %s")
                    % overlapping[0].name
                )
