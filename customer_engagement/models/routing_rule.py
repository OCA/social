from datetime import datetime

from odoo import api, fields, models


class EngageRoutingRule(models.Model):
    """Routing rules for automatic conversation assignment."""

    _name = "engage.routing.rule"
    _description = "Engage Routing Rule"
    _order = "sequence, id"

    name = fields.Char(string="Rule Name", required=True)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    description = fields.Text(string="Description")

    # ==================== Conditions ====================

    # Channel condition
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
        help="Match conversations from this channel",
    )

    # Partner conditions
    partner_vip = fields.Boolean(
        string="VIP Customers Only",
        default=False,
        help="Match only VIP customers",
    )
    partner_tag_ids = fields.Many2many(
        comodel_name="res.partner.category",
        relation="engage_routing_rule_partner_tag_rel",
        column1="rule_id",
        column2="tag_id",
        string="Customer Tags",
        help="Match customers with any of these tags",
    )
    partner_country_ids = fields.Many2many(
        comodel_name="res.country",
        relation="engage_routing_rule_country_rel",
        column1="rule_id",
        column2="country_id",
        string="Countries",
        help="Match customers from these countries",
    )

    # Content conditions
    keyword_match = fields.Char(
        string="Keywords",
        help="Comma-separated keywords to match in message content (case-insensitive)",
    )
    keyword_match_mode = fields.Selection(
        selection=[
            ("any", "Any Keyword"),
            ("all", "All Keywords"),
        ],
        string="Keyword Mode",
        default="any",
    )

    # Time conditions
    time_condition = fields.Selection(
        selection=[
            ("any", "Any Time"),
            ("business", "Business Hours"),
            ("outside", "Outside Business Hours"),
        ],
        string="Time Condition",
        default="any",
    )

    # Source team (optional - for escalation rules)
    source_team_id = fields.Many2one(
        comodel_name="engage.team",
        string="Source Team",
        help="Match conversations from this team (for escalation)",
    )

    # ==================== Actions ====================

    # Assignment actions
    target_team_id = fields.Many2one(
        comodel_name="engage.team",
        string="Assign to Team",
        help="Assign matching conversations to this team",
    )
    target_user_id = fields.Many2one(
        comodel_name="res.users",
        string="Assign to Agent",
        help="Assign directly to this agent (overrides team)",
    )
    use_team_assignment = fields.Boolean(
        string="Use Team Auto-Assignment",
        default=True,
        help="Use team's assignment method to pick agent",
    )

    # Property actions
    set_priority = fields.Selection(
        selection=[
            ("0", "Low"),
            ("1", "Normal"),
            ("2", "High"),
            ("3", "Urgent"),
        ],
        string="Set Priority",
    )
    add_label_ids = fields.Many2many(
        comodel_name="engage.conversation.label",
        relation="engage_routing_rule_label_rel",
        column1="rule_id",
        column2="label_id",
        string="Add Labels",
    )

    # Auto-response
    auto_message = fields.Text(
        string="Auto-Response Message",
        help="Send this message automatically when rule matches",
    )
    auto_message_delay = fields.Integer(
        string="Auto-Response Delay (sec)",
        default=0,
        help="Delay before sending auto-response",
    )

    # Statistics
    match_count = fields.Integer(
        string="Times Matched",
        default=0,
        readonly=True,
    )
    last_match_date = fields.Datetime(
        string="Last Match",
        readonly=True,
    )

    def _check_conditions(self, conversation, message_content=None):
        """
        Check if this rule's conditions match the conversation.

        :param conversation: engage.conversation record
        :param message_content: Optional message text to check keywords
        :return: True if all conditions match
        """
        self.ensure_one()

        # Channel condition
        if self.channel_type and conversation.channel_type != self.channel_type:
            return False

        # Partner conditions
        partner = conversation.partner_id
        if partner:
            if self.partner_vip and not partner.vip_customer:
                return False

            if self.partner_tag_ids:
                if not (set(self.partner_tag_ids.ids) & set(partner.category_id.ids)):
                    return False

            if self.partner_country_ids:
                if partner.country_id not in self.partner_country_ids:
                    return False
        elif self.partner_vip or self.partner_tag_ids or self.partner_country_ids:
            # Partner conditions specified but no partner
            return False

        # Keyword condition
        if self.keyword_match and message_content:
            keywords = [k.strip().lower() for k in self.keyword_match.split(",")]
            content_lower = message_content.lower()

            if self.keyword_match_mode == "all":
                if not all(kw in content_lower for kw in keywords):
                    return False
            else:  # any
                if not any(kw in content_lower for kw in keywords):
                    return False

        # Time condition
        if self.time_condition != "any":
            is_business_hours = self._is_business_hours()
            if self.time_condition == "business" and not is_business_hours:
                return False
            if self.time_condition == "outside" and is_business_hours:
                return False

        # Source team condition
        if self.source_team_id and conversation.team_id != self.source_team_id:
            return False

        return True

    def _is_business_hours(self):
        """
        Check if current time is within business hours.
        TODO: Use team schedule or company calendar.
        """
        now = datetime.now()
        # Simple check: Mon-Fri, 9:00-18:00
        if now.weekday() >= 5:  # Weekend
            return False
        if now.hour < 9 or now.hour >= 18:
            return False
        return True

    def _apply_actions(self, conversation):
        """
        Apply this rule's actions to the conversation.

        :param conversation: engage.conversation record
        """
        self.ensure_one()
        vals = {}

        # Team assignment
        if self.target_team_id:
            vals["team_id"] = self.target_team_id.id

            if self.use_team_assignment:
                # Let team's assignment method pick agent
                agent = self.target_team_id.get_available_agent(conversation)
                if agent:
                    vals["user_id"] = agent.id

        # Direct agent assignment (overrides team assignment)
        if self.target_user_id:
            vals["user_id"] = self.target_user_id.id

        # Priority
        if self.set_priority:
            vals["priority"] = self.set_priority

        # Write conversation updates
        if vals:
            conversation.write(vals)

        # Labels (separate write for M2M)
        if self.add_label_ids:
            conversation.write(
                {"label_ids": [(4, label_id) for label_id in self.add_label_ids.ids]}
            )

        # Auto-response
        if self.auto_message:
            # TODO: Implement delayed message with queue
            conversation.message_post(
                body=self.auto_message,
                message_type="comment",
            )

        # Update statistics
        self.sudo().write(
            {
                "match_count": self.match_count + 1,
                "last_match_date": fields.Datetime.now(),
            }
        )

    @api.model
    def apply_routing_rules(self, conversation, message_content=None):
        """
        Find and apply matching routing rules to a conversation.

        :param conversation: engage.conversation record
        :param message_content: Optional message content for keyword matching
        :return: engage.routing.rule that matched, or empty recordset
        """
        rules = self.search([("active", "=", True)], order="sequence")

        for rule in rules:
            if rule._check_conditions(conversation, message_content):
                rule._apply_actions(conversation)
                return rule

        return self.browse()


class ConversationRouting(models.Model):
    """Routing extension for engage.conversation."""

    _inherit = "engage.conversation"

    routing_rule_id = fields.Many2one(
        comodel_name="engage.routing.rule",
        string="Applied Routing Rule",
        readonly=True,
        help="The routing rule that was applied to this conversation",
    )

    @api.model_create_multi
    def create(self, vals_list):
        """Apply routing rules on conversation creation."""
        records = super().create(vals_list)

        for record in records:
            # Skip if already assigned
            if record.team_id or record.user_id:
                continue

            rule = self.env["engage.routing.rule"].apply_routing_rules(record)
            if rule:
                record.routing_rule_id = rule

        return records

    def action_apply_routing(self):
        """Manually apply routing rules."""
        for record in self:
            rule = self.env["engage.routing.rule"].apply_routing_rules(record)
            if rule:
                record.routing_rule_id = rule
