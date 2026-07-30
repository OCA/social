from odoo import fields, models, tools


class EngageMetrics(models.Model):
    """SQL View for engagement metrics and reporting."""

    _name = "engage.metrics"
    _description = "Engage Metrics"
    _auto = False
    _order = "date desc"

    # Dimensions
    date = fields.Date(string="Date", readonly=True)
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
        readonly=True,
    )
    team_id = fields.Many2one(
        comodel_name="engage.team",
        string="Team",
        readonly=True,
    )
    user_id = fields.Many2one(
        comodel_name="res.users",
        string="Agent",
        readonly=True,
    )

    # Conversation metrics
    conversation_count = fields.Integer(
        string="Total Conversations",
        readonly=True,
    )
    new_conversation_count = fields.Integer(
        string="New Conversations",
        readonly=True,
    )
    resolved_count = fields.Integer(
        string="Resolved",
        readonly=True,
    )
    closed_count = fields.Integer(
        string="Closed",
        readonly=True,
    )

    # Time metrics (in minutes)
    avg_first_response = fields.Float(
        string="Avg First Response (min)",
        readonly=True,
        group_operator="avg",
    )
    avg_resolution_time = fields.Float(
        string="Avg Resolution Time (min)",
        readonly=True,
        group_operator="avg",
    )

    # SLA metrics
    sla_achieved_count = fields.Integer(
        string="SLA Achieved",
        readonly=True,
    )
    sla_breached_count = fields.Integer(
        string="SLA Breached",
        readonly=True,
    )
    sla_rate = fields.Float(
        string="SLA Rate (%)",
        readonly=True,
        group_operator="avg",
    )

    # Message metrics
    message_count = fields.Integer(
        string="Total Messages",
        readonly=True,
    )
    inbound_message_count = fields.Integer(
        string="Inbound Messages",
        readonly=True,
    )
    outbound_message_count = fields.Integer(
        string="Outbound Messages",
        readonly=True,
    )

    def init(self):
        """Create the SQL view for metrics."""
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute(f"""
            CREATE OR REPLACE VIEW {self._table} AS (
                SELECT
                    row_number() OVER () as id,
                    DATE(c.create_date) as date,
                    c.channel_type,
                    c.team_id,
                    c.user_id,

                    -- Conversation counts
                    COUNT(DISTINCT c.id) as conversation_count,
                    COUNT(DISTINCT c.id) FILTER (
                        WHERE DATE(c.create_date) = DATE(c.create_date)
                    ) as new_conversation_count,
                    COUNT(DISTINCT c.id) FILTER (
                        WHERE c.resolved_at IS NOT NULL
                    ) as resolved_count,
                    COUNT(DISTINCT c.id) FILTER (
                        WHERE cs.closed = TRUE
                    ) as closed_count,

                    -- Time metrics (in minutes)
                    AVG(
                        EXTRACT(EPOCH FROM (c.first_response_at - c.create_date)) / 60
                    ) FILTER (
                        WHERE c.first_response_at IS NOT NULL
                    ) as avg_first_response,
                    AVG(
                        EXTRACT(EPOCH FROM (c.resolved_at - c.create_date)) / 60
                    ) FILTER (
                        WHERE c.resolved_at IS NOT NULL
                    ) as avg_resolution_time,

                    -- SLA metrics
                    COUNT(DISTINCT c.id) FILTER (
                        WHERE c.sla_status = 'achieved'
                    ) as sla_achieved_count,
                    COUNT(DISTINCT c.id) FILTER (
                        WHERE c.sla_status = 'breached'
                    ) as sla_breached_count,
                    CASE
                        WHEN COUNT(DISTINCT c.id) FILTER (
                            WHERE c.sla_status IN ('achieved', 'breached')
                        ) > 0
                        THEN (
                            COUNT(DISTINCT c.id) FILTER (
                                WHERE c.sla_status = 'achieved'
                            )::float /
                            COUNT(DISTINCT c.id) FILTER (
                                WHERE c.sla_status IN ('achieved', 'breached')
                            ) * 100
                        )
                        ELSE 0
                    END as sla_rate,

                    -- Message counts (simplified - would need message table join)
                    0 as message_count,
                    0 as inbound_message_count,
                    0 as outbound_message_count

                FROM engage_conversation c
                LEFT JOIN engage_conversation_stage cs ON c.stage_id = cs.id
                GROUP BY
                    DATE(c.create_date),
                    c.channel_type,
                    c.team_id,
                    c.user_id
            )
        """)


class EngageMetricsAgent(models.Model):
    """SQL View for agent-level metrics."""

    _name = "engage.metrics.agent"
    _description = "Engage Agent Metrics"
    _auto = False
    _order = "date desc, user_id"

    date = fields.Date(string="Date", readonly=True)
    user_id = fields.Many2one(
        comodel_name="res.users",
        string="Agent",
        readonly=True,
    )

    # Activity metrics
    conversations_handled = fields.Integer(
        string="Conversations Handled",
        readonly=True,
    )
    conversations_resolved = fields.Integer(
        string="Conversations Resolved",
        readonly=True,
    )

    # Performance metrics
    avg_first_response = fields.Float(
        string="Avg First Response (min)",
        readonly=True,
        group_operator="avg",
    )
    avg_resolution_time = fields.Float(
        string="Avg Resolution Time (min)",
        readonly=True,
        group_operator="avg",
    )

    # SLA performance
    sla_achieved = fields.Integer(string="SLA Achieved", readonly=True)
    sla_breached = fields.Integer(string="SLA Breached", readonly=True)
    sla_rate = fields.Float(string="SLA Rate (%)", readonly=True)

    def init(self):
        """Create the SQL view for agent metrics."""
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute(f"""
            CREATE OR REPLACE VIEW {self._table} AS (
                SELECT
                    row_number() OVER () as id,
                    DATE(c.create_date) as date,
                    c.user_id,

                    COUNT(DISTINCT c.id) as conversations_handled,
                    COUNT(DISTINCT c.id) FILTER (
                        WHERE c.resolved_at IS NOT NULL
                    ) as conversations_resolved,

                    AVG(
                        EXTRACT(EPOCH FROM (c.first_response_at - c.create_date)) / 60
                    ) FILTER (
                        WHERE c.first_response_at IS NOT NULL
                    ) as avg_first_response,

                    AVG(
                        EXTRACT(EPOCH FROM (c.resolved_at - c.create_date)) / 60
                    ) FILTER (
                        WHERE c.resolved_at IS NOT NULL
                    ) as avg_resolution_time,

                    COUNT(DISTINCT c.id) FILTER (
                        WHERE c.sla_status = 'achieved'
                    ) as sla_achieved,
                    COUNT(DISTINCT c.id) FILTER (
                        WHERE c.sla_status = 'breached'
                    ) as sla_breached,
                    CASE
                        WHEN COUNT(DISTINCT c.id) FILTER (
                            WHERE c.sla_status IN ('achieved', 'breached')
                        ) > 0
                        THEN (
                            COUNT(DISTINCT c.id) FILTER (
                                WHERE c.sla_status = 'achieved'
                            )::float /
                            COUNT(DISTINCT c.id) FILTER (
                                WHERE c.sla_status IN ('achieved', 'breached')
                            ) * 100
                        )
                        ELSE 0
                    END as sla_rate

                FROM engage_conversation c
                WHERE c.user_id IS NOT NULL
                GROUP BY DATE(c.create_date), c.user_id
            )
        """)


class EngageMetricsChannel(models.Model):
    """SQL View for channel-level metrics."""

    _name = "engage.metrics.channel"
    _description = "Engage Channel Metrics"
    _auto = False
    _order = "date desc, channel_type"

    date = fields.Date(string="Date", readonly=True)
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
        readonly=True,
    )

    conversation_count = fields.Integer(string="Conversations", readonly=True)
    resolved_count = fields.Integer(string="Resolved", readonly=True)
    avg_resolution_time = fields.Float(
        string="Avg Resolution (min)",
        readonly=True,
    )
    sla_rate = fields.Float(string="SLA Rate (%)", readonly=True)

    def init(self):
        """Create the SQL view for channel metrics."""
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute(f"""
            CREATE OR REPLACE VIEW {self._table} AS (
                SELECT
                    row_number() OVER () as id,
                    DATE(c.create_date) as date,
                    c.channel_type,

                    COUNT(DISTINCT c.id) as conversation_count,
                    COUNT(DISTINCT c.id) FILTER (
                        WHERE c.resolved_at IS NOT NULL
                    ) as resolved_count,

                    AVG(
                        EXTRACT(EPOCH FROM (c.resolved_at - c.create_date)) / 60
                    ) FILTER (
                        WHERE c.resolved_at IS NOT NULL
                    ) as avg_resolution_time,

                    CASE
                        WHEN COUNT(DISTINCT c.id) FILTER (
                            WHERE c.sla_status IN ('achieved', 'breached')
                        ) > 0
                        THEN (
                            COUNT(DISTINCT c.id) FILTER (
                                WHERE c.sla_status = 'achieved'
                            )::float /
                            COUNT(DISTINCT c.id) FILTER (
                                WHERE c.sla_status IN ('achieved', 'breached')
                            ) * 100
                        )
                        ELSE 0
                    END as sla_rate

                FROM engage_conversation c
                GROUP BY DATE(c.create_date), c.channel_type
            )
        """)
