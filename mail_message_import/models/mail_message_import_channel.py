# Copyright 2026 Binhex
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import json
from collections import defaultdict
from datetime import datetime, timedelta

from babel.dates import format_date

from odoo import api, fields, models
from odoo.tools.misc import get_lang

# Days of the graph of the panel, and its bars while no message arrived.
GRAPH_DAYS = 7
SAMPLE_GRAPH = [3, 5, 2, 6, 4, 7, 5]


class MailMessageImportChannel(models.Model):
    """Where the senders send their messages: a WhatsApp number, an email
    address...

    This module knows no channel type: each channel module (email, WhatsApp...)
    adds its value to ``channel_type``, the fields it needs to receive and the
    state of its channels (``_channel_state``).
    """

    _name = "mail.message.import.channel"
    _description = "Receiving Channel"
    _order = "sequence, id"
    _check_company_auto = True

    name = fields.Char(required=True)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    company_id = fields.Many2one(
        "res.company", required=True, default=lambda self: self.env.company
    )
    channel_type = fields.Selection(
        selection=[],
        string="Channel",
        default=lambda self: self._default_channel_type(),
        help="How the messages arrive. Each channel is a module.",
    )
    state = fields.Selection(
        [
            ("not_configured", "Not configured"),
            ("pending", "Pending verification"),
            ("connected", "Connected"),
            ("disabled", "Disabled"),
        ],
        compute="_compute_state",
    )
    state_message = fields.Char(compute="_compute_state")
    last_message_date = fields.Datetime(compute="_compute_counters")
    message_count = fields.Integer(compute="_compute_counters")
    unidentified_count = fields.Integer(compute="_compute_counters")
    waiting_count = fields.Integer(compute="_compute_counters")
    error_count = fields.Integer(compute="_compute_counters")
    open_incident_count = fields.Integer(compute="_compute_counters")
    dashboard_graph = fields.Text(compute="_compute_dashboard_graph")

    def _default_channel_type(self):
        """The channel, when a single one is installed."""
        channel_types = self._fields["channel_type"].get_values(self.env)
        return channel_types[0] if len(channel_types) == 1 else False

    @api.depends("active", "channel_type")
    def _compute_state(self):
        for channel in self:
            if channel.active:
                state, message = channel._channel_state()
            else:
                state, message = "disabled", False
            channel.state = state
            channel.state_message = message

    def _channel_state(self):
        """The state of an active channel and what it lacks, as
        ``(state, message)``. Each channel module tells it for its own."""
        self.ensure_one()
        return "not_configured", self.env._(
            "Choose how the messages arrive. Each channel (email, WhatsApp...) "
            "is a module."
        )

    def _compute_counters(self):
        Message = self.env["mail.message.import.message"]
        Conversation = self.env["mail.message.import.conversation"]
        Incident = self.env["mail.message.import.incident"]
        for channel in self:
            domain = [("channel_id", "=", channel.id)]
            channel.message_count = Message.search_count(domain)
            channel.unidentified_count = Message.search_count(
                domain + [("state", "=", "unidentified")]
            )
            channel.waiting_count = Conversation.search_count(
                domain + [("state", "in", ("open", "processing"))]
            )
            channel.error_count = Conversation.search_count(
                domain + [("state", "=", "error")]
            )
            channel.open_incident_count = Incident.search_count(
                domain + [("state", "=", "open")]
            )
            # Computed, not stored: writing it on every message would make the
            # concurrent messages of a channel conflict.
            channel.last_message_date = Message.search(
                domain, order="received_date desc", limit=1
            ).received_date

    def _origin_text(self, address, sender_address):
        """Where a message comes from: "WhatsApp · +34 600 000 000 (Ana)"."""
        self.ensure_one()
        channel_types = dict(
            self._fields["channel_type"]._description_selection(self.env)
        )
        parts = [
            channel_types.get(self.channel_type) or self.name,
            address.address or sender_address,
        ]
        text = " · ".join(part for part in parts if part)
        if address.name:
            text = f"{text} ({address.name})"
        return text

    def _compute_dashboard_graph(self):
        """The messages received in the last days, in the bars of the panel."""
        today = fields.Date.context_today(self)
        days = [today - timedelta(days=ago) for ago in range(GRAPH_DAYS - 1, -1, -1)]
        counts = defaultdict(int)
        groups = self.env["mail.message.import.message"]._read_group(
            [
                ("channel_id", "in", self.ids),
                ("received_date", ">=", fields.Datetime.to_datetime(days[0])),
            ],
            ["channel_id", "received_date:day"],
            ["__count"],
        )
        for channel, day, count in groups:
            if isinstance(day, datetime):
                day = day.date()
            counts[channel.id, day] += count
        locale = get_lang(self.env).code
        for channel in self:
            values = [
                {
                    "label": format_date(day, "EEE d", locale=locale),
                    "value": counts[channel.id, day],
                    "type": "past",
                }
                for day in days
            ]
            sample = not any(value["value"] for value in values)
            if sample:
                for value, sample_value in zip(values, SAMPLE_GRAPH, strict=True):
                    value.update(value=sample_value, type="sample")
            channel.dashboard_graph = json.dumps(
                [
                    {
                        "values": values,
                        "key": self.env._("Messages received"),
                        "is_sample_data": sample,
                    }
                ]
            )

    def _action_related(self, xmlid, domain, context=None):
        action = self.env["ir.actions.act_window"]._for_xml_id(xmlid)
        action["domain"] = domain
        action["context"] = context or {}
        return action

    def action_view_messages(self):
        return self._action_related(
            "mail_message_import.action_mail_message_import_message",
            [("channel_id", "in", self.ids)],
        )

    def action_view_unidentified(self):
        return self._action_related(
            "mail_message_import.action_mail_message_import_message",
            [("channel_id", "in", self.ids), ("state", "=", "unidentified")],
        )

    def action_view_conversations(self):
        return self._action_related(
            "mail_message_import.action_mail_message_import_conversation",
            [("channel_id", "in", self.ids)],
        )

    def action_view_waiting(self):
        return self._action_related(
            "mail_message_import.action_mail_message_import_conversation",
            [("channel_id", "in", self.ids)],
            {"search_default_waiting": 1},
        )

    def action_view_errors(self):
        return self._action_related(
            "mail_message_import.action_mail_message_import_conversation",
            [("channel_id", "in", self.ids)],
            {"search_default_error": 1},
        )

    def action_view_incidents(self):
        return self._action_related(
            "mail_message_import.action_mail_message_import_incident",
            [("channel_id", "in", self.ids)],
            {"search_default_open": 1},
        )
