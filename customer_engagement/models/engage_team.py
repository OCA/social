"""Engage Team Model."""

import pytz

from odoo import api, fields, models


def _tz_get(self):
    """Get list of timezones."""
    return [
        (tz, tz)
        for tz in sorted(
            pytz.all_timezones, key=lambda tz: tz if not tz.startswith("Etc/") else "_"
        )
    ]


class EngageTeam(models.Model):
    """Teams for organizing agents and routing conversations."""

    _name = "engage.team"
    _description = "Engage Team"
    _order = "sequence, name"

    name = fields.Char(
        required=True,
        translate=True,
    )
    sequence = fields.Integer(
        default=10,
    )
    description = fields.Text(
        translate=True,
    )
    active = fields.Boolean(
        default=True,
    )
    color = fields.Integer(
        string="Color Index",
        default=0,
    )
    member_ids = fields.Many2many(
        comodel_name="res.users",
        relation="engage_team_user_rel",
        column1="team_id",
        column2="user_id",
        string="Team Members",
    )
    leader_id = fields.Many2one(
        comodel_name="res.users",
        string="Team Leader",
        domain="[('id', 'in', member_ids)]",
    )
    channel_types = fields.Selection(
        selection=[
            ("all", "All Channels"),
            ("selected", "Selected Channels"),
        ],
        string="Channel Assignment",
        default="all",
        help="Define which channels this team handles",
    )
    allowed_channel_ids = fields.Char(
        string="Allowed Channels",
        help="Comma-separated list of channel types (e.g., 'whatsapp,email')",
    )
    auto_assign = fields.Boolean(
        string="Auto-assign Conversations",
        default=False,
        help="Automatically assign new conversations to team members",
    )
    assignment_method = fields.Selection(
        selection=[
            ("round_robin", "Round Robin"),
            ("least_loaded", "Least Loaded"),
            ("preferred", "Preferred Agent"),
            ("manual", "Manual"),
        ],
        default="manual",
        help="Method for automatic agent assignment:\n"
        "- Round Robin: Distribute evenly among agents\n"
        "- Least Loaded: Assign to agent with fewest open conversations\n"
        "- Preferred Agent: Try last agent who helped the customer\n"
        "- Manual: No automatic assignment",
    )
    max_conversations_per_agent = fields.Integer(
        string="Max Conversations per Agent",
        default=0,
        help="Maximum open conversations per agent (0 = unlimited)",
    )

    # Schedule fields
    schedule_ids = fields.One2many(
        "engage.team.schedule",
        "team_id",
        string="Working Hours",
    )
    timezone = fields.Selection(
        _tz_get,
        string="Timezone",
        default=lambda self: self.env.user.tz or "UTC",
    )
    is_open = fields.Boolean(
        compute="_compute_is_open",
        string="Currently Open",
    )

    # Messages
    welcome_message = fields.Text(
        string="Welcome Message",
        translate=True,
        help="Message sent when a new conversation is assigned to this team",
    )
    out_of_hours_message = fields.Text(
        string="Out of Hours Message",
        translate=True,
        help="Message sent when customer contacts outside working hours",
    )

    # Computed counts
    conversation_count = fields.Integer(
        string="Open Conversations",
        compute="_compute_conversation_count",
    )
    member_count = fields.Integer(
        string="Members",
        compute="_compute_member_count",
    )

    def _compute_conversation_count(self):
        """Count open conversations assigned to this team."""
        for team in self:
            team.conversation_count = self.env["engage.conversation"].search_count(
                [("team_id", "=", team.id), ("closed", "=", False)]
            )

    @api.depends("member_ids")
    def _compute_member_count(self):
        """Count team members."""
        for team in self:
            team.member_count = len(team.member_ids)

    def _compute_is_open(self):
        """Check if team is currently within working hours."""
        for team in self:
            team.is_open = team._check_is_open()

    def _check_is_open(self):
        """Check if team is currently within working hours."""
        self.ensure_one()
        if not self.schedule_ids:
            # No schedule defined, always open
            return True

        # Get current time in team timezone
        tz = pytz.timezone(self.timezone or "UTC")
        now = fields.Datetime.context_timestamp(self, fields.Datetime.now())
        if self.timezone:
            now = now.astimezone(tz)

        day = str(now.weekday())
        current_time = now.hour + now.minute / 60.0

        # Check if current time falls within any schedule for today
        schedules = self.schedule_ids.filtered(lambda s: s.day_of_week == day)
        for schedule in schedules:
            if schedule.start_time <= current_time <= schedule.end_time:
                return True
        return False

    def _get_available_members(self):
        """Get list of available team members respecting capacity limits."""
        self.ensure_one()
        if not self.member_ids:
            return self.env["res.users"]

        available = self.member_ids.filtered(lambda u: u.active and not u.share)

        # Filter by engage status if using res.users extension
        if hasattr(available, "engage_is_available"):
            available = available.filtered(lambda u: u.engage_is_available)
        elif self.max_conversations_per_agent:
            # Manual capacity check
            result = self.env["res.users"]
            for member in available:
                count = self.env["engage.conversation"].search_count(
                    [("user_id", "=", member.id), ("closed", "=", False)]
                )
                if count < self.max_conversations_per_agent:
                    result |= member
            available = result

        return available

    def get_available_agent(self, conversation=None):
        """Get the next available agent for assignment based on method."""
        self.ensure_one()
        available_members = self._get_available_members()
        if not available_members:
            return False

        if self.assignment_method == "preferred" and conversation:
            agent = self._get_preferred_agent(conversation, available_members)
            if agent:
                return agent
            # Fallback to least_loaded
            return self._get_least_loaded_agent(available_members)

        elif self.assignment_method == "round_robin":
            return self._get_round_robin_agent(available_members)

        elif self.assignment_method == "least_loaded":
            return self._get_least_loaded_agent(available_members)

        return False

    def _get_preferred_agent(self, conversation, available_members):
        """Try to get the last agent who helped this customer."""
        if not conversation.partner_id:
            return False

        # Find last conversation with this customer that had an assigned agent
        last_conv = self.env["engage.conversation"].search(
            [
                ("partner_id", "=", conversation.partner_id.id),
                ("user_id", "!=", False),
                ("id", "!=", conversation.id if conversation.id else 0),
            ],
            limit=1,
            order="id desc",
        )

        if last_conv and last_conv.user_id in available_members:
            return last_conv.user_id
        return False

    def _get_round_robin_agent(self, available_members):
        """Get next agent in round-robin fashion."""
        last_conv = self.env["engage.conversation"].search(
            [("team_id", "=", self.id), ("user_id", "!=", False)],
            order="create_date desc",
            limit=1,
        )
        if last_conv and last_conv.user_id in available_members:
            members_list = list(available_members)
            idx = members_list.index(last_conv.user_id)
            next_idx = (idx + 1) % len(members_list)
            return members_list[next_idx]
        return available_members[0] if available_members else False

    def _get_least_loaded_agent(self, available_members):
        """Get agent with fewest open conversations."""
        min_count = float("inf")
        best_agent = False
        for member in available_members:
            count = self.env["engage.conversation"].search_count(
                [("user_id", "=", member.id), ("closed", "=", False)]
            )
            if count < min_count:
                min_count = count
                best_agent = member
        return best_agent
