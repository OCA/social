import logging
from datetime import timedelta

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class EngageAutomation(models.Model):
    """Automation rules triggered by conversation events."""

    _name = "engage.automation"
    _description = "Engage Automation"
    _order = "sequence, id"

    name = fields.Char(string="Name", required=True)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    description = fields.Text(string="Description")

    # Trigger configuration
    trigger_event = fields.Selection(
        selection=[
            ("conversation_created", "New Conversation"),
            ("message_received", "Message Received"),
            ("conversation_idle", "Conversation Idle"),
            ("sla_warning", "SLA Warning"),
            ("sla_breach", "SLA Breach"),
            ("stage_changed", "Stage Changed"),
            ("assigned", "Conversation Assigned"),
            ("unassigned", "Conversation Unassigned"),
        ],
        string="Trigger Event",
        required=True,
        help="Event that triggers this automation",
    )

    # Delay settings
    trigger_delay = fields.Integer(
        string="Delay (minutes)",
        default=0,
        help="Minutes to wait before executing actions",
    )
    idle_minutes = fields.Integer(
        string="Idle Time (minutes)",
        default=30,
        help="Minutes of inactivity before triggering (for idle trigger)",
    )

    # Conditions
    channel_type = fields.Selection(
        selection=[
            ("email", "Email"),
            ("whatsapp", "WhatsApp"),
            ("instagram", "Instagram"),
            ("messenger", "Messenger"),
            ("telegram", "Telegram"),
            ("livechat", "Live Chat"),
            ("api", "API"),
        ],
        string="Channel",
        help="Only trigger for this channel (empty = all)",
    )
    team_ids = fields.Many2many(
        comodel_name="engage.team",
        relation="engage_automation_team_rel",
        column1="automation_id",
        column2="team_id",
        string="Teams",
        help="Only trigger for conversations in these teams (empty = all)",
    )
    priority_filter = fields.Selection(
        selection=[
            ("0", "Low"),
            ("1", "Normal"),
            ("2", "High"),
            ("3", "Urgent"),
        ],
        string="Priority",
        help="Only trigger for this priority (empty = all)",
    )
    stage_ids = fields.Many2many(
        comodel_name="engage.conversation.stage",
        relation="engage_automation_stage_rel",
        column1="automation_id",
        column2="stage_id",
        string="Stages",
        help="Only trigger for conversations in these stages (empty = all)",
    )

    # Actions
    action_ids = fields.One2many(
        comodel_name="engage.automation.action",
        inverse_name="automation_id",
        string="Actions",
    )

    # Statistics
    execution_count = fields.Integer(
        string="Executions",
        default=0,
        readonly=True,
    )
    last_execution = fields.Datetime(
        string="Last Execution",
        readonly=True,
    )
    error_count = fields.Integer(
        string="Errors",
        default=0,
        readonly=True,
    )

    def _check_conditions(self, conversation):
        """
        Check if automation conditions match the conversation.

        :param conversation: engage.conversation record
        :return: True if conditions match
        """
        self.ensure_one()

        # Channel condition
        if self.channel_type and conversation.channel_type != self.channel_type:
            return False

        # Team condition
        if self.team_ids and conversation.team_id not in self.team_ids:
            return False

        # Priority condition
        if self.priority_filter and conversation.priority != self.priority_filter:
            return False

        # Stage condition
        if self.stage_ids and conversation.stage_id not in self.stage_ids:
            return False

        return True

    def _execute(self, conversation):
        """
        Execute all actions for this automation.

        :param conversation: engage.conversation record
        """
        self.ensure_one()

        try:
            for action in self.action_ids.sorted("sequence"):
                action._execute(conversation)

            # Update statistics
            self.sudo().write(
                {
                    "execution_count": self.execution_count + 1,
                    "last_execution": fields.Datetime.now(),
                }
            )

        except Exception as e:
            _logger.exception(
                "Automation %s failed for conversation %s: %s",
                self.name,
                conversation.id,
                str(e),
            )
            self.sudo().write(
                {
                    "error_count": self.error_count + 1,
                }
            )

    @api.model
    def _trigger_automations(self, event, conversation, **kwargs):
        """
        Find and execute matching automations for an event.

        :param event: Event type string
        :param conversation: engage.conversation record
        :param kwargs: Additional context
        """
        automations = self.search(
            [
                ("active", "=", True),
                ("trigger_event", "=", event),
            ],
            order="sequence",
        )

        for automation in automations:
            if automation._check_conditions(conversation):
                if automation.trigger_delay > 0:
                    # Schedule delayed execution
                    self.env["engage.automation.queue"].create(
                        {
                            "automation_id": automation.id,
                            "conversation_id": conversation.id,
                            "scheduled_at": fields.Datetime.now()
                            + timedelta(minutes=automation.trigger_delay),
                        }
                    )
                else:
                    automation._execute(conversation)

    @api.model
    def _cron_check_idle_conversations(self):
        """Cron job to check for idle conversations."""
        automations = self.search(
            [
                ("active", "=", True),
                ("trigger_event", "=", "conversation_idle"),
            ]
        )

        for automation in automations:
            idle_threshold = fields.Datetime.now() - timedelta(
                minutes=automation.idle_minutes
            )

            # Find conversations that are idle
            domain = [
                ("closed", "=", False),
                ("write_date", "<", idle_threshold),
            ]

            # Add automation conditions
            if automation.channel_type:
                domain.append(("channel_type", "=", automation.channel_type))
            if automation.team_ids:
                domain.append(("team_id", "in", automation.team_ids.ids))
            if automation.priority_filter:
                domain.append(("priority", "=", automation.priority_filter))
            if automation.stage_ids:
                domain.append(("stage_id", "in", automation.stage_ids.ids))

            conversations = self.env["engage.conversation"].search(domain)

            for conv in conversations:
                # Check if already processed recently
                if not self._was_recently_triggered(automation, conv):
                    automation._execute(conv)

    def _was_recently_triggered(self, automation, conversation):
        """Check if this automation was recently triggered for this conversation."""
        # Could implement using a log table
        # For now, return False
        return False

    @api.model
    def _cron_process_queue(self):
        """Process delayed automation queue."""
        now = fields.Datetime.now()
        queue_items = self.env["engage.automation.queue"].search(
            [
                ("scheduled_at", "<=", now),
                ("processed", "=", False),
            ]
        )

        for item in queue_items:
            if item.automation_id.active and item.conversation_id.exists():
                item.automation_id._execute(item.conversation_id)
            item.processed = True


class EngageAutomationAction(models.Model):
    """Actions to execute as part of an automation."""

    _name = "engage.automation.action"
    _description = "Engage Automation Action"
    _order = "sequence, id"

    automation_id = fields.Many2one(
        comodel_name="engage.automation",
        string="Automation",
        required=True,
        ondelete="cascade",
    )
    sequence = fields.Integer(default=10)

    action_type = fields.Selection(
        selection=[
            ("send_message", "Send Message"),
            ("add_label", "Add Label"),
            ("remove_label", "Remove Label"),
            ("assign_team", "Assign to Team"),
            ("assign_user", "Assign to Agent"),
            ("unassign", "Unassign"),
            ("change_stage", "Change Stage"),
            ("set_priority", "Set Priority"),
            ("notify_user", "Notify User"),
            ("notify_team", "Notify Team"),
            ("webhook", "Call Webhook"),
            ("add_note", "Add Internal Note"),
        ],
        string="Action Type",
        required=True,
    )

    # Parameters for different action types
    # Message
    message_content = fields.Text(
        string="Message Content",
        help="Message to send (supports placeholders: {partner_name}, {agent_name})",
    )
    message_is_note = fields.Boolean(
        string="As Internal Note",
        default=False,
    )

    # Labels
    label_ids = fields.Many2many(
        comodel_name="engage.conversation.label",
        relation="engage_automation_action_label_rel",
        column1="action_id",
        column2="label_id",
        string="Labels",
    )

    # Assignment
    team_id = fields.Many2one(
        comodel_name="engage.team",
        string="Team",
    )
    user_id = fields.Many2one(
        comodel_name="res.users",
        string="Agent",
    )
    use_team_assignment = fields.Boolean(
        string="Use Team Assignment",
        default=True,
        help="Use team's assignment method to pick agent",
    )

    # Stage
    stage_id = fields.Many2one(
        comodel_name="engage.conversation.stage",
        string="Stage",
    )

    # Priority
    priority = fields.Selection(
        selection=[
            ("0", "Low"),
            ("1", "Normal"),
            ("2", "High"),
            ("3", "Urgent"),
        ],
        string="Priority",
    )

    # Notification
    notify_user_ids = fields.Many2many(
        comodel_name="res.users",
        relation="engage_automation_action_notify_rel",
        column1="action_id",
        column2="user_id",
        string="Users to Notify",
    )
    notification_message = fields.Text(
        string="Notification Message",
    )

    # Webhook
    webhook_url = fields.Char(string="Webhook URL")
    webhook_method = fields.Selection(
        selection=[
            ("POST", "POST"),
            ("GET", "GET"),
        ],
        string="HTTP Method",
        default="POST",
    )

    def _execute(self, conversation):
        """
        Execute this action on a conversation.

        :param conversation: engage.conversation record
        """
        self.ensure_one()

        method_name = f"_action_{self.action_type}"
        if hasattr(self, method_name):
            getattr(self, method_name)(conversation)
        else:
            _logger.warning("Unknown action type: %s", self.action_type)

    def _format_message(self, template, conversation):
        """Format message template with conversation data."""
        return template.format(
            partner_name=conversation.partner_id.name or "Customer",
            agent_name=conversation.user_id.name or "Agent",
            conversation_id=conversation.uuid[:8],
            channel=conversation.channel_type,
            subject=conversation.subject or "",
        )

    def _action_send_message(self, conversation):
        """Send a message to the conversation."""
        if not self.message_content:
            return

        body = self._format_message(self.message_content, conversation)

        if self.message_is_note:
            conversation.action_add_note(body)
        else:
            conversation.message_post(
                body=body,
                message_type="comment",
            )

    def _action_add_label(self, conversation):
        """Add labels to the conversation."""
        if self.label_ids:
            conversation.write(
                {"label_ids": [(4, label_id) for label_id in self.label_ids.ids]}
            )

    def _action_remove_label(self, conversation):
        """Remove labels from the conversation."""
        if self.label_ids:
            conversation.write(
                {"label_ids": [(3, label_id) for label_id in self.label_ids.ids]}
            )

    def _action_assign_team(self, conversation):
        """Assign conversation to a team."""
        if not self.team_id:
            return

        vals = {"team_id": self.team_id.id}

        if self.use_team_assignment:
            agent = self.team_id.get_available_agent(conversation)
            if agent:
                vals["user_id"] = agent.id

        conversation.write(vals)

    def _action_assign_user(self, conversation):
        """Assign conversation to a specific agent."""
        if self.user_id:
            conversation.write({"user_id": self.user_id.id})

    def _action_unassign(self, conversation):
        """Unassign the conversation."""
        conversation.write({"user_id": False})

    def _action_change_stage(self, conversation):
        """Change conversation stage."""
        if self.stage_id:
            try:
                conversation.write({"stage_id": self.stage_id.id})
            except Exception as e:
                _logger.warning("Could not change stage: %s", e)

    def _action_set_priority(self, conversation):
        """Set conversation priority."""
        if self.priority:
            conversation.write({"priority": self.priority})

    def _action_notify_user(self, conversation):
        """Send notification to users."""
        if not self.notify_user_ids:
            return

        message = self._format_message(
            self.notification_message
            or "Automation notification for conversation {conversation_id}",
            conversation,
        )

        for user in self.notify_user_ids:
            # Use Odoo's notification system
            self.env["bus.bus"]._sendone(
                user.partner_id,
                "simple_notification",
                {
                    "title": "Engagement Automation",
                    "message": message,
                    "sticky": False,
                    "type": "info",
                },
            )

    def _action_notify_team(self, conversation):
        """Send notification to team members."""
        team = self.team_id or conversation.team_id
        if not team:
            return

        message = self._format_message(
            self.notification_message
            or "Automation notification for conversation {conversation_id}",
            conversation,
        )

        for member in team.member_ids:
            self.env["bus.bus"]._sendone(
                member.partner_id,
                "simple_notification",
                {
                    "title": "Engagement Automation",
                    "message": message,
                    "sticky": False,
                    "type": "info",
                },
            )

    def _action_webhook(self, conversation):
        """Call external webhook."""
        if not self.webhook_url:
            return

        import requests

        payload = {
            "event": self.automation_id.trigger_event,
            "conversation_id": conversation.id,
            "conversation_uuid": conversation.uuid,
            "partner_id": conversation.partner_id.id
            if conversation.partner_id
            else None,
            "partner_name": conversation.partner_id.name
            if conversation.partner_id
            else None,
            "channel_type": conversation.channel_type,
            "stage": conversation.stage_id.code if conversation.stage_id else None,
        }

        try:
            if self.webhook_method == "POST":
                requests.post(self.webhook_url, json=payload, timeout=10)
            else:
                requests.get(self.webhook_url, params=payload, timeout=10)
        except Exception as e:
            _logger.error("Webhook call failed: %s", e)

    def _action_add_note(self, conversation):
        """Add an internal note."""
        if self.message_content:
            body = self._format_message(self.message_content, conversation)
            conversation.action_add_note(body)


class EngageAutomationQueue(models.Model):
    """Queue for delayed automation execution."""

    _name = "engage.automation.queue"
    _description = "Engage Automation Queue"
    _order = "scheduled_at"

    automation_id = fields.Many2one(
        comodel_name="engage.automation",
        string="Automation",
        required=True,
        ondelete="cascade",
    )
    conversation_id = fields.Many2one(
        comodel_name="engage.conversation",
        string="Conversation",
        required=True,
        ondelete="cascade",
    )
    scheduled_at = fields.Datetime(
        string="Scheduled At",
        required=True,
    )
    processed = fields.Boolean(
        string="Processed",
        default=False,
    )


class ConversationAutomation(models.Model):
    """Automation triggers integration for conversations."""

    _inherit = "engage.conversation"

    @api.model_create_multi
    def create(self, vals_list):
        """Trigger automations on conversation creation."""
        records = super().create(vals_list)

        for record in records:
            self.env["engage.automation"]._trigger_automations(
                "conversation_created", record
            )

        return records

    def write(self, vals):
        """Trigger automations on specific changes."""
        # Track changes for automation triggers
        old_stages = {r.id: r.stage_id for r in self}
        old_users = {r.id: r.user_id for r in self}

        result = super().write(vals)

        # Trigger stage change automations
        if "stage_id" in vals:
            for record in self:
                if old_stages.get(record.id) != record.stage_id:
                    self.env["engage.automation"]._trigger_automations(
                        "stage_changed", record
                    )

        # Trigger assignment automations
        if "user_id" in vals:
            for record in self:
                old_user = old_users.get(record.id)
                if record.user_id and not old_user:
                    self.env["engage.automation"]._trigger_automations(
                        "assigned", record
                    )
                elif not record.user_id and old_user:
                    self.env["engage.automation"]._trigger_automations(
                        "unassigned", record
                    )

        return result
