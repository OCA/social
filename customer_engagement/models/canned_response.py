"""Canned Response Model."""

from odoo import fields, models


class CannedResponse(models.Model):
    """Pre-defined responses for quick replies."""

    _name = "support.canned.response"
    _description = "Canned Response"
    _order = "sequence, shortcut"

    name = fields.Char(
        string="Title",
        required=True,
        translate=True,
        help="Descriptive name for the response",
    )
    shortcut = fields.Char(
        required=True,
        help="Type / followed by this shortcut to insert (e.g., /greeting)",
    )
    content = fields.Html(
        required=True,
        translate=True,
        sanitize=True,
        help="The response text to insert",
    )
    plain_content = fields.Text(
        compute="_compute_plain_content",
        store=True,
        help="Plain text version of content for preview",
    )
    sequence = fields.Integer(
        default=10,
    )
    active = fields.Boolean(
        default=True,
    )
    category = fields.Selection(
        selection=[
            ("greeting", "Greetings"),
            ("closing", "Closings"),
            ("info", "Information"),
            ("apology", "Apologies"),
            ("followup", "Follow-ups"),
            ("other", "Other"),
        ],
        default="other",
    )
    channel_types = fields.Char(
        string="Channels",
        help="Comma-separated channel types, empty = all channels",
    )
    team_ids = fields.Many2many(
        comodel_name="support.team",
        relation="canned_response_team_rel",
        column1="response_id",
        column2="team_id",
        string="Teams",
        help="Restrict to specific teams, empty = all teams",
    )
    user_id = fields.Many2one(
        comodel_name="res.users",
        string="Owner",
        help="If set, only this user can use this response",
    )
    usage_count = fields.Integer(
        default=0,
        help="Number of times this response has been used",
    )

    _sql_constraints = [
        (
            "shortcut_unique",
            "UNIQUE(shortcut)",
            "Shortcut must be unique!",
        ),
    ]

    def _compute_plain_content(self):
        """Extract plain text from HTML content."""
        from odoo.tools import html2plaintext

        for response in self:
            if response.content:
                response.plain_content = html2plaintext(response.content)[:200]
            else:
                response.plain_content = ""

    def increment_usage(self):
        """Increment usage count when response is used."""
        for response in self:
            response.sudo().write({"usage_count": response.usage_count + 1})

    def search_by_shortcut(
        self, shortcut, channel_type=None, team_id=None, user_id=None
    ):
        """Search for canned responses matching a shortcut prefix."""
        domain = [
            ("active", "=", True),
            ("shortcut", "ilike", shortcut),
        ]

        responses = self.search(domain, order="sequence, shortcut", limit=10)

        # Filter by channel type if specified
        if channel_type:
            responses = responses.filtered(
                lambda r: not r.channel_types
                or channel_type in r.channel_types.split(",")
            )

        # Filter by team if specified
        if team_id:
            team = self.env["support.team"].browse(team_id)
            responses = responses.filtered(
                lambda r: not r.team_ids or team in r.team_ids
            )

        # Filter by user (personal responses)
        if user_id:
            responses = responses.filtered(
                lambda r: not r.user_id or r.user_id.id == user_id
            )

        return responses
