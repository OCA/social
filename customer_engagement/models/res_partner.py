from odoo import api, fields, models


class ResPartner(models.Model):
    """Extension of res.partner for omnichannel customer profile."""

    _inherit = "res.partner"

    # Channel identifiers
    whatsapp_number = fields.Char(
        string="WhatsApp Number",
        index=True,
        help="WhatsApp phone number with country code (e.g., +5511999999999)",
    )
    telegram_id = fields.Char(
        string="Telegram ID",
        index=True,
        help="Telegram user ID or username",
    )
    instagram_id = fields.Char(
        string="Instagram ID",
        index=True,
        help="Instagram user ID or handle",
    )
    messenger_id = fields.Char(
        string="Messenger ID",
        index=True,
        help="Facebook Messenger PSID",
    )

    # Engagement conversations
    engage_conversation_ids = fields.One2many(
        comodel_name="engage.conversation",
        inverse_name="partner_id",
        string="Conversations",
    )
    engage_conversation_count = fields.Integer(
        string="Total Conversations",
        compute="_compute_conversation_stats",
        store=True,
    )
    open_conversation_count = fields.Integer(
        string="Open Conversations",
        compute="_compute_conversation_stats",
        store=True,
    )
    last_conversation_date = fields.Datetime(
        string="Last Conversation",
        compute="_compute_conversation_stats",
        store=True,
    )

    # Customer preferences
    preferred_channel = fields.Selection(
        selection=[
            ("whatsapp", "WhatsApp"),
            ("email", "Email"),
            ("telegram", "Telegram"),
            ("instagram", "Instagram"),
            ("messenger", "Messenger"),
            ("phone", "Phone Call"),
        ],
        string="Preferred Channel",
        help="Customer's preferred communication channel",
    )
    vip_customer = fields.Boolean(
        string="VIP Customer",
        default=False,
        help="Mark as VIP for priority routing",
    )
    engage_blocked = fields.Boolean(
        string="Blocked from Engagement",
        default=False,
        help="Block this contact from creating new conversations",
    )
    notes_for_agents = fields.Text(
        string="Notes for Agents",
        help="Internal notes visible to support agents",
    )

    # Engagement metrics
    avg_resolution_time = fields.Float(
        string="Avg Resolution Time (hours)",
        compute="_compute_engagement_metrics",
        help="Average time to resolve conversations with this customer",
    )
    satisfaction_score = fields.Float(
        string="Satisfaction Score",
        compute="_compute_engagement_metrics",
        help="Average CSAT score from this customer",
    )
    total_messages_received = fields.Integer(
        string="Messages Received",
        compute="_compute_engagement_metrics",
        help="Total messages received from this customer",
    )

    @api.depends("engage_conversation_ids", "engage_conversation_ids.closed")
    def _compute_conversation_stats(self):
        for partner in self:
            conversations = partner.engage_conversation_ids
            partner.engage_conversation_count = len(conversations)
            partner.open_conversation_count = len(
                conversations.filtered(lambda c: not c.closed)
            )
            if conversations:
                partner.last_conversation_date = max(
                    conversations.mapped("create_date")
                )
            else:
                partner.last_conversation_date = False

    def _compute_engagement_metrics(self):
        """Compute engagement metrics for the partner."""
        for partner in self:
            conversations = partner.engage_conversation_ids.filtered(
                lambda c: c.resolved_at and c.create_date
            )

            # Average resolution time
            if conversations:
                total_time = sum(
                    (c.resolved_at - c.create_date).total_seconds() / 3600
                    for c in conversations
                )
                partner.avg_resolution_time = total_time / len(conversations)
            else:
                partner.avg_resolution_time = 0.0

            # Satisfaction score (placeholder - will be computed from CSAT model)
            partner.satisfaction_score = 0.0

            # Total messages (count mail.messages for this partner's conversations)
            partner.total_messages_received = self.env["mail.message"].search_count(
                [
                    ("model", "=", "engage.conversation"),
                    ("res_id", "in", partner.engage_conversation_ids.ids),
                    ("message_type", "!=", "notification"),
                ]
            )

    @api.model
    def _find_by_channel_id(self, channel_type, channel_id):
        """
        Find partner by channel identifier.

        :param channel_type: Type of channel (whatsapp, telegram, instagram, messenger)
        :param channel_id: The identifier on that channel
        :return: res.partner record or empty recordset
        """
        field_map = {
            "whatsapp": "whatsapp_number",
            "telegram": "telegram_id",
            "instagram": "instagram_id",
            "messenger": "messenger_id",
        }
        field = field_map.get(channel_type)
        if field:
            return self.search([(field, "=", channel_id)], limit=1)
        # For email channel, search by email
        if channel_type == "email":
            return self.search([("email", "=ilike", channel_id)], limit=1)
        return self.browse()

    @api.model
    def _find_or_create_by_channel(self, channel_type, channel_id, name=None):
        """
        Find or create partner by channel identifier.

        :param channel_type: Type of channel
        :param channel_id: The identifier on that channel
        :param name: Optional name for new partner
        :return: res.partner record
        """
        partner = self._find_by_channel_id(channel_type, channel_id)
        if partner:
            return partner

        # Create new partner
        field_map = {
            "whatsapp": "whatsapp_number",
            "telegram": "telegram_id",
            "instagram": "instagram_id",
            "messenger": "messenger_id",
            "email": "email",
        }
        field = field_map.get(channel_type)
        if not field:
            return self.browse()

        vals = {
            field: channel_id,
            "name": name or f"{channel_type.title()} User {channel_id[-4:]}",
        }

        # Set phone/mobile for WhatsApp
        if channel_type == "whatsapp":
            vals["mobile"] = channel_id

        return self.create(vals)

    def action_view_conversations(self):
        """Open conversations for this partner."""
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": f"Conversations - {self.name}",
            "res_model": "engage.conversation",
            "view_mode": "tree,form",
            "domain": [("partner_id", "=", self.id)],
            "context": {"default_partner_id": self.id},
        }
