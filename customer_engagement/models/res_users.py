from odoo import api, fields, models


class ResUsers(models.Model):
    """Extension of res.users for agent profile and status."""

    _inherit = "res.users"

    # Agent status
    engage_status = fields.Selection(
        selection=[
            ("online", "Online"),
            ("busy", "Busy"),
            ("away", "Away"),
            ("offline", "Offline"),
        ],
        string="Engagement Status",
        default="offline",
        help="Current availability status for handling conversations",
    )

    # Capacity settings
    engage_max_conversations = fields.Integer(
        string="Max Conversations",
        default=5,
        help="Maximum number of simultaneous conversations this agent can handle",
    )

    # Computed fields
    engage_active_count = fields.Integer(
        string="Active Conversations",
        compute="_compute_engage_stats",
        help="Number of currently assigned open conversations",
    )
    engage_is_available = fields.Boolean(
        string="Available",
        compute="_compute_engage_stats",
        help="Whether agent is available to receive new conversations",
    )
    engage_today_resolved = fields.Integer(
        string="Resolved Today",
        compute="_compute_engage_stats",
        help="Conversations resolved today",
    )

    # Preferences
    engage_signature = fields.Text(
        string="Signature",
        help="Signature to append to messages",
    )
    engage_sound_notifications = fields.Boolean(
        string="Sound Notifications",
        default=True,
        help="Play sound for new messages",
    )
    engage_desktop_notifications = fields.Boolean(
        string="Desktop Notifications",
        default=True,
        help="Show desktop notifications for new messages",
    )
    engage_auto_accept = fields.Boolean(
        string="Auto-Accept Assignments",
        default=True,
        help="Automatically accept conversation assignments",
    )

    # Team membership
    engage_team_ids = fields.Many2many(
        comodel_name="engage.team",
        relation="engage_team_user_rel",
        column1="user_id",
        column2="team_id",
        string="Engage Teams",
    )

    # Skills/specializations for routing
    engage_skill_ids = fields.Many2many(
        comodel_name="engage.conversation.label",
        relation="engage_user_skill_rel",
        column1="user_id",
        column2="label_id",
        string="Skills",
        help="Labels/topics this agent specializes in",
    )

    @api.depends("engage_status", "engage_max_conversations")
    def _compute_engage_stats(self):
        """Compute engagement statistics for the agent."""
        Conversation = self.env["engage.conversation"]
        today_start = fields.Datetime.today()

        for user in self:
            # Active conversations
            active_count = Conversation.search_count(
                [
                    ("user_id", "=", user.id),
                    ("closed", "=", False),
                ]
            )
            user.engage_active_count = active_count

            # Is available
            user.engage_is_available = (
                user.engage_status == "online"
                and active_count < user.engage_max_conversations
            )

            # Resolved today
            user.engage_today_resolved = Conversation.search_count(
                [
                    ("user_id", "=", user.id),
                    ("resolved_at", ">=", today_start),
                ]
            )

    def action_set_status(self, status):
        """Set agent status."""
        self.ensure_one()
        if status in ("online", "busy", "away", "offline"):
            self.engage_status = status

    def action_go_online(self):
        """Set status to online."""
        self.action_set_status("online")

    def action_go_offline(self):
        """Set status to offline."""
        self.action_set_status("offline")

    def action_go_busy(self):
        """Set status to busy."""
        self.action_set_status("busy")

    def action_go_away(self):
        """Set status to away."""
        self.action_set_status("away")

    @api.model
    def get_available_agents(self, team_id=None, skill_ids=None):
        """
        Get list of available agents.

        :param team_id: Optional team filter
        :param skill_ids: Optional skill/label IDs filter
        :return: res.users recordset
        """
        domain = [
            ("engage_status", "=", "online"),
            ("share", "=", False),  # Internal users only
        ]

        if team_id:
            domain.append(("engage_team_ids", "in", [team_id]))

        agents = self.search(domain)

        # Filter by capacity
        agents = agents.filtered(lambda u: u.engage_is_available)

        # Filter by skills if specified
        if skill_ids:
            agents = agents.filtered(
                lambda u: bool(set(skill_ids) & set(u.engage_skill_ids.ids))
            )

        return agents

    @api.model
    def _get_agent_stats(self, user_ids=None, date_from=None, date_to=None):
        """
        Get agent performance statistics.

        :param user_ids: Optional list of user IDs
        :param date_from: Start date for stats
        :param date_to: End date for stats
        :return: dict with stats per user
        """
        domain = [("user_id", "!=", False)]

        if user_ids:
            domain.append(("user_id", "in", user_ids))
        if date_from:
            domain.append(("create_date", ">=", date_from))
        if date_to:
            domain.append(("create_date", "<=", date_to))

        conversations = self.env["engage.conversation"].search(domain)

        stats = {}
        for conv in conversations:
            user_id = conv.user_id.id
            if user_id not in stats:
                stats[user_id] = {
                    "total": 0,
                    "resolved": 0,
                    "avg_response_time": 0,
                    "response_times": [],
                }

            stats[user_id]["total"] += 1
            if conv.resolved_at:
                stats[user_id]["resolved"] += 1

            if conv.first_response_at and conv.create_date:
                response_time = (
                    conv.first_response_at - conv.create_date
                ).total_seconds()
                stats[user_id]["response_times"].append(response_time)

        # Calculate averages
        for user_id, data in stats.items():
            if data["response_times"]:
                data["avg_response_time"] = sum(data["response_times"]) / len(
                    data["response_times"]
                )
            del data["response_times"]

        return stats
