import uuid as uuid_lib

from odoo import api, fields, models
from odoo.exceptions import UserError

# Valid transitions mapping
VALID_TRANSITIONS = {
    "new": ["open"],
    "open": ["pending", "resolved"],
    "pending": ["open", "resolved"],
    "resolved": ["open", "closed"],
    "closed": ["open"],
}


class Conversation(models.Model):
    _name = "engage.conversation"
    _description = "Engagement Conversation"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "priority desc, create_date desc"
    _rec_name = "display_name"

    # Identification
    uuid = fields.Char(
        string="UUID",
        default=lambda self: str(uuid_lib.uuid4()),
        readonly=True,
        index=True,
        copy=False,
    )
    subject = fields.Char()
    display_name = fields.Char(compute="_compute_display_name", store=True)

    # Channel
    channel_type = fields.Selection(
        [
            ("email", "Email"),
            ("whatsapp", "WhatsApp"),
            ("instagram", "Instagram"),
            ("messenger", "Messenger"),
            ("telegram", "Telegram"),
            ("livechat", "Live Chat"),
            ("api", "API"),
        ],
        string="Channel",
        required=True,
        index=True,
        tracking=True,
    )
    channel_identifier = fields.Char(
        string="Channel Identifier",
        index=True,
        help="External identifier on the channel (phone number, email, user ID, etc.)",
    )
    channel_conversation_id = fields.Char(
        string="External Conversation ID",
        index=True,
        help="Conversation ID from the external channel",
    )
    channel_metadata = fields.Json(
        string="Channel Metadata",
        help="Additional channel-specific metadata (JSON format)",
    )

    # Stage (state machine)
    stage_id = fields.Many2one(
        comodel_name="engage.conversation.stage",
        string="Stage",
        tracking=True,
        index=True,
        group_expand="_read_group_stage_ids",
        default=lambda self: self._default_stage(),
        copy=False,
    )
    closed = fields.Boolean(related="stage_id.closed", store=True)

    # Priority
    priority = fields.Selection(
        [
            ("0", "Low"),
            ("1", "Normal"),
            ("2", "High"),
            ("3", "Urgent"),
        ],
        default="1",
        index=True,
        tracking=True,
    )

    # Relationships
    partner_id = fields.Many2one(
        comodel_name="res.partner",
        string="Contact",
        index=True,
        tracking=True,
    )
    user_id = fields.Many2one(
        comodel_name="res.users",
        string="Assigned Agent",
        index=True,
        tracking=True,
    )

    # Timestamps
    first_response_at = fields.Datetime(string="First Response", readonly=True)
    resolved_at = fields.Datetime(readonly=True)
    closed_date = fields.Datetime(string="Closed Date", readonly=True)

    # Computed time metrics
    response_time_seconds = fields.Integer(
        compute="_compute_time_metrics",
        store=True,
        string="Response Time (seconds)",
        help="Time from creation to first response",
    )
    resolution_time_seconds = fields.Integer(
        compute="_compute_time_metrics",
        store=True,
        string="Resolution Time (seconds)",
        help="Time from creation to resolution",
    )

    # Waiting status
    is_waiting_customer = fields.Boolean(
        compute="_compute_waiting_status",
        store=True,
        string="Waiting for Customer",
    )
    is_waiting_agent = fields.Boolean(
        compute="_compute_waiting_status",
        store=True,
        string="Waiting for Agent",
    )
    last_customer_message_date = fields.Datetime(
        compute="_compute_last_messages",
        store=True,
        string="Last Customer Message",
    )
    last_agent_message_date = fields.Datetime(
        compute="_compute_last_messages",
        store=True,
        string="Last Agent Message",
    )

    # Color for Kanban
    color = fields.Integer(string="Color Index")

    # History
    history_ids = fields.One2many(
        comodel_name="engage.conversation.history",
        inverse_name="conversation_id",
        string="History",
    )

    # Labels (tags)
    label_ids = fields.Many2many(
        comodel_name="engage.conversation.label",
        relation="engage_conversation_label_rel",
        column1="conversation_id",
        column2="label_id",
        string="Labels",
    )

    # Team assignment
    team_id = fields.Many2one(
        comodel_name="engage.team",
        string="Team",
        index=True,
        tracking=True,
    )

    # Folders
    folder_ids = fields.Many2many(
        comodel_name="engage.folder",
        relation="engage_conversation_folder_rel",
        column1="conversation_id",
        column2="folder_id",
        string="Folders",
    )

    # Private notes
    note_ids = fields.One2many(
        comodel_name="engage.conversation.note",
        inverse_name="conversation_id",
        string="Notes",
    )

    # Computed fields for UI
    unread_message_count = fields.Integer(
        string="Unread Messages",
        compute="_compute_unread_count",
        store=False,
    )
    last_message_preview = fields.Char(
        string="Last Message",
        compute="_compute_last_message",
        store=False,
    )
    last_message_date = fields.Datetime(
        compute="_compute_last_message",
        store=False,
    )
    note_count = fields.Integer(
        string="Notes Count",
        compute="_compute_note_count",
    )

    # Computed methods for UI fields
    def _compute_unread_count(self):
        """Compute unread messages count."""
        for rec in self:
            # Count messages not authored by internal users
            # author_id is res.partner, check if it has no linked user
            messages = self.env["mail.message"].search_count(
                [
                    ("model", "=", "engage.conversation"),
                    ("res_id", "=", rec.id),
                    ("message_type", "in", ["comment", "email"]),
                    (
                        "author_id.user_ids",
                        "=",
                        False,
                    ),  # External author (no linked user)
                ]
            )
            rec.unread_message_count = messages

    def _compute_last_message(self):
        """Compute last message preview and date."""
        for rec in self:
            last_message = self.env["mail.message"].search(
                [
                    ("model", "=", "engage.conversation"),
                    ("res_id", "=", rec.id),
                    ("message_type", "in", ["comment", "email"]),
                ],
                order="date desc",
                limit=1,
            )
            if last_message:
                # Strip HTML and truncate
                from odoo.tools import html2plaintext

                plain_text = html2plaintext(last_message.body or "")
                rec.last_message_preview = plain_text[:100] if plain_text else ""
                rec.last_message_date = last_message.date
            else:
                rec.last_message_preview = ""
                rec.last_message_date = False

    @api.depends("note_ids")
    def _compute_note_count(self):
        """Compute notes count."""
        for rec in self:
            rec.note_count = len(rec.note_ids)

    @api.depends("first_response_at", "resolved_at", "create_date")
    def _compute_time_metrics(self):
        """Compute response and resolution time in seconds."""
        for rec in self:
            if rec.first_response_at and rec.create_date:
                delta = rec.first_response_at - rec.create_date
                rec.response_time_seconds = int(delta.total_seconds())
            else:
                rec.response_time_seconds = 0

            if rec.resolved_at and rec.create_date:
                delta = rec.resolved_at - rec.create_date
                rec.resolution_time_seconds = int(delta.total_seconds())
            else:
                rec.resolution_time_seconds = 0

    def _compute_last_messages(self):
        """Compute last message dates for customer and agent."""
        for rec in self:
            messages = self.env["mail.message"].search(
                [
                    ("model", "=", "engage.conversation"),
                    ("res_id", "=", rec.id),
                    ("message_type", "in", ["comment", "email"]),
                ],
                order="date desc",
            )

            rec.last_customer_message_date = False
            rec.last_agent_message_date = False

            for msg in messages:
                # Check if author is internal (has linked user)
                is_internal = msg.author_id and msg.author_id.user_ids
                if is_internal and not rec.last_agent_message_date:
                    rec.last_agent_message_date = msg.date
                elif not is_internal and not rec.last_customer_message_date:
                    rec.last_customer_message_date = msg.date
                if rec.last_customer_message_date and rec.last_agent_message_date:
                    break

    @api.depends("last_customer_message_date", "last_agent_message_date", "closed")
    def _compute_waiting_status(self):
        """Compute who is waiting based on last messages."""
        for rec in self:
            if rec.closed:
                rec.is_waiting_customer = False
                rec.is_waiting_agent = False
            elif not rec.last_customer_message_date and not rec.last_agent_message_date:
                # New conversation, waiting for agent
                rec.is_waiting_customer = False
                rec.is_waiting_agent = True
            elif not rec.last_agent_message_date:
                # Only customer messages, waiting for agent
                rec.is_waiting_customer = False
                rec.is_waiting_agent = True
            elif not rec.last_customer_message_date:
                # Only agent messages, waiting for customer
                rec.is_waiting_customer = True
                rec.is_waiting_agent = False
            elif rec.last_customer_message_date > rec.last_agent_message_date:
                # Customer sent last, waiting for agent
                rec.is_waiting_customer = False
                rec.is_waiting_agent = True
            else:
                # Agent sent last, waiting for customer
                rec.is_waiting_customer = True
                rec.is_waiting_agent = False

    # Computed
    @api.depends("uuid", "subject", "partner_id")
    def _compute_display_name(self):
        for rec in self:
            if rec.subject:
                rec.display_name = f"[{rec.uuid[:8]}] {rec.subject}"
            elif rec.partner_id:
                rec.display_name = f"[{rec.uuid[:8]}] {rec.partner_id.name}"
            else:
                rec.display_name = f"[{rec.uuid[:8]}]"

    def _default_stage(self):
        return self.env["engage.conversation.stage"].search(
            [("code", "=", "new")], limit=1
        )

    @api.model
    def _read_group_stage_ids(self, stages, domain):
        return self.env["engage.conversation.stage"].search([])

    def write(self, vals):
        if "stage_id" in vals:
            new_stage = self.env["engage.conversation.stage"].browse(vals["stage_id"])
            for rec in self:
                if rec.stage_id:
                    rec._validate_transition(rec.stage_id.code, new_stage.code)
                rec._record_transition(new_stage)
                rec._update_timestamps(new_stage)
        return super().write(vals)

    def _validate_transition(self, from_code, to_code):
        """Validate that the state transition is allowed."""
        if from_code == to_code:
            return
        valid_targets = VALID_TRANSITIONS.get(from_code, [])
        if to_code not in valid_targets:
            raise UserError(
                f"Invalid transition: {from_code} → {to_code}. "
                f"Allowed: {', '.join(valid_targets)}"
            )

    def _record_transition(self, new_stage):
        """Record transition in history."""
        self.env["engage.conversation.history"].create(
            {
                "conversation_id": self.id,
                "from_stage_id": self.stage_id.id if self.stage_id else False,
                "to_stage_id": new_stage.id,
                "user_id": self.env.uid,
            }
        )

    def _update_timestamps(self, new_stage):
        """Update relevant timestamps on transition."""
        vals = {}
        if new_stage.code == "open" and not self.first_response_at:
            vals["first_response_at"] = fields.Datetime.now()
        if new_stage.code == "resolved" and not self.resolved_at:
            vals["resolved_at"] = fields.Datetime.now()
        if new_stage.code == "closed" and not self.closed_date:
            vals["closed_date"] = fields.Datetime.now()
        if new_stage.code == "open":
            # Reopening - clear resolved and closed timestamps
            if self.resolved_at:
                vals["resolved_at"] = False
            if self.closed_date:
                vals["closed_date"] = False
        if vals:
            return super().write(vals)
        return True

    # Action buttons
    def action_open(self):
        """Move to open stage."""
        stage = self.env["engage.conversation.stage"].search(
            [("code", "=", "open")], limit=1
        )
        self.write({"stage_id": stage.id})

    def action_resolve(self):
        """Move to resolved stage."""
        stage = self.env["engage.conversation.stage"].search(
            [("code", "=", "resolved")], limit=1
        )
        self.write({"stage_id": stage.id})

    def action_close(self):
        """Move to closed stage."""
        stage = self.env["engage.conversation.stage"].search(
            [("code", "=", "closed")], limit=1
        )
        self.write({"stage_id": stage.id})

    def action_pending(self):
        """Move to pending stage."""
        stage = self.env["engage.conversation.stage"].search(
            [("code", "=", "pending")], limit=1
        )
        self.write({"stage_id": stage.id})

    def action_assign_to_me(self):
        """Assign conversation to current user."""
        self.write({"user_id": self.env.uid})

    def action_add_note(self, content):
        """Add a private note to the conversation."""
        self.env["engage.conversation.note"].create(
            {
                "conversation_id": self.id,
                "author_id": self.env.uid,
                "content": content,
            }
        )

    def action_add_label(self, label_id):
        """Add a label to the conversation."""
        self.write({"label_ids": [(4, label_id)]})

    def action_remove_label(self, label_id):
        """Remove a label from the conversation."""
        self.write({"label_ids": [(3, label_id)]})

    def action_assign_team(self, team_id):
        """Assign conversation to a team."""
        team = self.env["engage.team"].browse(team_id)
        vals = {"team_id": team_id}
        if team.auto_assign:
            agent = team.get_available_agent(conversation=self)
            if agent:
                vals["user_id"] = agent.id
        self.write(vals)

    def action_add_to_folder(self, folder_id):
        """Add conversation to a folder."""
        self.write({"folder_ids": [(4, folder_id)]})

    def action_remove_from_folder(self, folder_id):
        """Remove conversation from a folder."""
        self.write({"folder_ids": [(3, folder_id)]})

    def init(self):
        """Create database indexes for performance."""
        self.env.cr.execute(
            """
            CREATE INDEX IF NOT EXISTS engage_conversation_stage_user_idx
            ON engage_conversation (stage_id, user_id)
            WHERE user_id IS NOT NULL;

            CREATE INDEX IF NOT EXISTS engage_conversation_channel_stage_idx
            ON engage_conversation (channel_type, stage_id);

            CREATE INDEX IF NOT EXISTS engage_conversation_partner_idx
            ON engage_conversation (partner_id)
            WHERE partner_id IS NOT NULL;

            CREATE INDEX IF NOT EXISTS engage_conversation_create_date_idx
            ON engage_conversation (create_date DESC);
        """
        )
