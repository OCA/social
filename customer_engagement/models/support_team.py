"""Support Team Model."""

from odoo import api, fields, models


class SupportTeam(models.Model):
    """Support teams for organizing agents and routing conversations."""

    _name = "support.team"
    _description = "Support Team"
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
        relation="support_team_user_rel",
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
            ("manual", "Manual"),
        ],
        default="manual",
    )
    max_conversations_per_agent = fields.Integer(
        string="Max Conversations per Agent",
        default=0,
        help="Maximum open conversations per agent (0 = unlimited)",
    )
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
            team.conversation_count = self.env["support.conversation"].search_count(
                [("team_id", "=", team.id), ("closed", "=", False)]
            )

    @api.depends("member_ids")
    def _compute_member_count(self):
        """Count team members."""
        for team in self:
            team.member_count = len(team.member_ids)

    def get_available_agent(self):
        """Get the next available agent for assignment based on method."""
        self.ensure_one()
        if not self.member_ids:
            return False

        available_members = self.member_ids.filtered(lambda u: u.active and not u.share)
        if not available_members:
            return False

        if self.assignment_method == "round_robin":
            # Get last assigned agent and rotate
            last_conv = self.env["support.conversation"].search(
                [("team_id", "=", self.id), ("user_id", "!=", False)],
                order="create_date desc",
                limit=1,
            )
            if last_conv and last_conv.user_id in available_members:
                idx = list(available_members).index(last_conv.user_id)
                next_idx = (idx + 1) % len(available_members)
                return available_members[next_idx]
            return available_members[0]

        elif self.assignment_method == "least_loaded":
            # Find agent with least open conversations
            min_count = float("inf")
            best_agent = False
            for member in available_members:
                count = self.env["support.conversation"].search_count(
                    [
                        ("user_id", "=", member.id),
                        ("closed", "=", False),
                    ]
                )
                if (
                    self.max_conversations_per_agent
                    and count >= self.max_conversations_per_agent
                ):
                    continue
                if count < min_count:
                    min_count = count
                    best_agent = member
            return best_agent

        return False
