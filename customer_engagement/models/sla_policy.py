from datetime import timedelta

from odoo import api, fields, models


class EngageSLAPolicy(models.Model):
    """SLA Policy for conversation handling."""

    _name = "engage.sla.policy"
    _description = "Engage SLA Policy"
    _order = "sequence, name"

    name = fields.Char(string="Policy Name", required=True)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    description = fields.Text(string="Description")

    # Time targets (in minutes)
    first_response_time = fields.Integer(
        string="First Response Time (min)",
        required=True,
        default=30,
        help="Target time for first agent response",
    )
    resolution_time = fields.Integer(
        string="Resolution Time (min)",
        required=True,
        default=480,
        help="Target time for conversation resolution",
    )

    # Conditions for applying this policy
    priority = fields.Selection(
        selection=[
            ("0", "Low"),
            ("1", "Normal"),
            ("2", "High"),
            ("3", "Urgent"),
        ],
        string="Priority",
        help="Apply to conversations with this priority (empty = all)",
    )
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
        help="Apply to conversations from this channel (empty = all)",
    )
    team_ids = fields.Many2many(
        comodel_name="engage.team",
        relation="engage_sla_policy_team_rel",
        column1="policy_id",
        column2="team_id",
        string="Teams",
        help="Apply to conversations assigned to these teams (empty = all)",
    )
    vip_only = fields.Boolean(
        string="VIP Customers Only",
        default=False,
        help="Apply only to VIP customers",
    )

    # Thresholds for alerts
    warning_threshold = fields.Integer(
        string="Warning Threshold (%)",
        default=80,
        help="Show warning when this percentage of time has elapsed",
    )
    critical_threshold = fields.Integer(
        string="Critical Threshold (%)",
        default=95,
        help="Show critical alert when this percentage of time has elapsed",
    )

    # Business hours
    business_hours_only = fields.Boolean(
        string="Business Hours Only",
        default=True,
        help="Only count business hours for SLA calculation",
    )

    # Statistics
    conversation_count = fields.Integer(
        string="Active Conversations",
        compute="_compute_stats",
    )
    achieved_rate = fields.Float(
        string="Achievement Rate (%)",
        compute="_compute_stats",
    )

    def _compute_stats(self):
        """Compute SLA statistics."""
        for policy in self:
            conversations = self.env["engage.conversation"].search(
                [
                    ("sla_policy_id", "=", policy.id),
                ]
            )
            policy.conversation_count = len(conversations)

            achieved = conversations.filtered(lambda c: c.sla_status == "achieved")
            total_closed = conversations.filtered(lambda c: c.closed)

            if total_closed:
                policy.achieved_rate = (len(achieved) / len(total_closed)) * 100
            else:
                policy.achieved_rate = 0.0

    @api.model
    def _get_matching_policy(self, conversation):
        """
        Find the best matching SLA policy for a conversation.

        :param conversation: engage.conversation record
        :return: engage.sla.policy record or empty recordset
        """
        domain = [("active", "=", True)]

        # Find all active policies and filter
        policies = self.search(domain, order="sequence")

        for policy in policies:
            # Check priority match
            if policy.priority and policy.priority != conversation.priority:
                continue

            # Check channel match
            if policy.channel_type and policy.channel_type != conversation.channel_type:
                continue

            # Check team match
            if policy.team_ids and conversation.team_id not in policy.team_ids:
                continue

            # Check VIP
            if policy.vip_only:
                if (
                    not conversation.partner_id
                    or not conversation.partner_id.vip_customer
                ):
                    continue

            # All conditions match
            return policy

        return self.browse()

    def calculate_deadline(self, start_time, minutes):
        """
        Calculate deadline from start time.

        :param start_time: datetime
        :param minutes: int
        :return: datetime
        """
        # TODO: Implement business hours calculation
        # For now, simple addition
        return start_time + timedelta(minutes=minutes)


class ConversationSLA(models.Model):
    """SLA fields extension for engage.conversation."""

    _inherit = "engage.conversation"

    # SLA policy
    sla_policy_id = fields.Many2one(
        comodel_name="engage.sla.policy",
        string="SLA Policy",
        tracking=True,
    )

    # Deadlines (computed and stored)
    sla_first_response_deadline = fields.Datetime(
        string="First Response Deadline",
        compute="_compute_sla_deadlines",
        store=True,
    )
    sla_resolution_deadline = fields.Datetime(
        string="Resolution Deadline",
        compute="_compute_sla_deadlines",
        store=True,
    )

    # Status
    sla_status = fields.Selection(
        selection=[
            ("pending", "Pending"),
            ("ok", "On Track"),
            ("warning", "Warning"),
            ("critical", "Critical"),
            ("breached", "Breached"),
            ("achieved", "Achieved"),
        ],
        string="SLA Status",
        compute="_compute_sla_status",
        store=True,
        help="Current SLA status based on deadlines",
    )

    # Tracking
    sla_first_response_breached = fields.Boolean(
        string="First Response Breached",
        compute="_compute_sla_status",
        store=True,
    )
    sla_resolution_breached = fields.Boolean(
        string="Resolution Breached",
        compute="_compute_sla_status",
        store=True,
    )

    @api.depends("sla_policy_id", "create_date")
    def _compute_sla_deadlines(self):
        """Compute SLA deadlines based on policy."""
        for conv in self:
            if conv.sla_policy_id and conv.create_date:
                policy = conv.sla_policy_id

                conv.sla_first_response_deadline = policy.calculate_deadline(
                    conv.create_date, policy.first_response_time
                )
                conv.sla_resolution_deadline = policy.calculate_deadline(
                    conv.create_date, policy.resolution_time
                )
            else:
                conv.sla_first_response_deadline = False
                conv.sla_resolution_deadline = False

    @api.depends(
        "sla_policy_id",
        "sla_first_response_deadline",
        "sla_resolution_deadline",
        "first_response_at",
        "resolved_at",
        "closed",
    )
    def _compute_sla_status(self):
        """Compute current SLA status."""
        now = fields.Datetime.now()

        for conv in self:
            if not conv.sla_policy_id:
                conv.sla_status = False
                conv.sla_first_response_breached = False
                conv.sla_resolution_breached = False
                continue

            policy = conv.sla_policy_id

            # Check first response breach
            if conv.first_response_at:
                conv.sla_first_response_breached = (
                    conv.first_response_at > conv.sla_first_response_deadline
                    if conv.sla_first_response_deadline
                    else False
                )
            else:
                conv.sla_first_response_breached = (
                    now > conv.sla_first_response_deadline
                    if conv.sla_first_response_deadline
                    else False
                )

            # Check resolution breach
            if conv.resolved_at:
                conv.sla_resolution_breached = (
                    conv.resolved_at > conv.sla_resolution_deadline
                    if conv.sla_resolution_deadline
                    else False
                )
            else:
                conv.sla_resolution_breached = (
                    now > conv.sla_resolution_deadline
                    if conv.sla_resolution_deadline
                    else False
                )

            # Determine overall status
            if conv.closed:
                if conv.sla_first_response_breached or conv.sla_resolution_breached:
                    conv.sla_status = "breached"
                else:
                    conv.sla_status = "achieved"
            elif conv.sla_first_response_breached or conv.sla_resolution_breached:
                conv.sla_status = "breached"
            else:
                # Check warning/critical thresholds
                if conv.sla_resolution_deadline:
                    total_time = (
                        conv.sla_resolution_deadline - conv.create_date
                    ).total_seconds()
                    elapsed_time = (now - conv.create_date).total_seconds()

                    if total_time > 0:
                        percentage = (elapsed_time / total_time) * 100

                        if percentage >= policy.critical_threshold:
                            conv.sla_status = "critical"
                        elif percentage >= policy.warning_threshold:
                            conv.sla_status = "warning"
                        else:
                            conv.sla_status = "ok"
                    else:
                        conv.sla_status = "ok"
                else:
                    conv.sla_status = "pending"

    @api.model_create_multi
    def create(self, vals_list):
        """Auto-assign SLA policy on creation."""
        records = super().create(vals_list)

        for record in records:
            if not record.sla_policy_id:
                policy = self.env["engage.sla.policy"]._get_matching_policy(record)
                if policy:
                    record.sla_policy_id = policy

        return records

    def action_update_sla(self):
        """Manually reassign SLA policy."""
        for record in self:
            policy = self.env["engage.sla.policy"]._get_matching_policy(record)
            record.sla_policy_id = policy if policy else False
