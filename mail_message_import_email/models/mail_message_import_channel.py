# Copyright 2026 Binhex
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools import email_normalize, email_normalize_all

from .fetchmail_server import CHANNEL_CONTEXT_KEY, SERVER_CONTEXT_KEY


class MailMessageImportChannel(models.Model):
    """An email address that receives messages.

    The emails of the address are read by an incoming mail server of Odoo,
    whose records are the received messages.
    """

    _inherit = "mail.message.import.channel"

    channel_type = fields.Selection(selection_add=[("email", "Email")])
    email_address = fields.Char(
        string="Receiving address",
        help="Address the senders write or forward their messages to, e.g. "
        "orders@company.com. Its mailbox must be read only by this channel.",
    )
    fetchmail_server_id = fields.Many2one(
        "fetchmail.server",
        string="Incoming mail server",
        ondelete="restrict",
        domain="[('object_id.model', '=', 'mail.message.import.message')]",
        help="Server of Odoo that reads the mailbox of the address: each email "
        "becomes a received message of the channel.",
    )

    _sql_constraints = [
        (
            "fetchmail_server_uniq",
            "unique(fetchmail_server_id)",
            "This incoming mail server already reads another receiving channel.",
        ),
    ]

    @api.constrains("channel_type", "email_address", "active")
    def _check_email(self):
        for channel in self.filtered(lambda c: c.channel_type == "email"):
            address = email_normalize(channel.email_address or "")
            if not address:
                raise ValidationError(
                    self.env._(
                        "Write a valid receiving address, e.g. orders@company.com."
                    )
                )
            others = [
                other
                for other in self.sudo().search(
                    [("channel_type", "=", "email"), ("id", "!=", channel.id)]
                )
                if email_normalize(other.email_address or "") == address
            ]
            if channel.active and others:
                raise ValidationError(
                    self.env._(
                        "The address %(email)s already receives messages in %(name)s.",
                        email=address,
                        name=others[0].name,
                    )
                )

    @api.constrains("fetchmail_server_id")
    def _check_fetchmail_server(self):
        for channel in self.sudo():
            server = channel.fetchmail_server_id
            if server and server.object_id.model != "mail.message.import.message":
                raise ValidationError(
                    self.env._(
                        "The incoming mail server %(server)s must create received "
                        "messages: set 'Create a new record' to 'Received Message'.",
                        server=server.name,
                    )
                )

    @api.depends(
        "email_address",
        "fetchmail_server_id.active",
        "fetchmail_server_id.state",
    )
    def _compute_state(self):
        return super()._compute_state()

    def _channel_state(self):
        if self.channel_type != "email":
            return super()._channel_state()
        server = self.fetchmail_server_id.sudo()
        missing = [
            label
            for label, value in (
                (self.env._("receiving address"), self.email_address),
                (self.env._("incoming mail server"), server),
            )
            if not value
        ]
        if missing:
            return "not_configured", self.env._(
                "Missing: %(fields)s.", fields=", ".join(missing)
            )
        if not server.active or server.state != "done":
            return "pending", self.env._(
                "Test and confirm the incoming mail server, and keep it active: "
                "until then no email is read."
            )
        return "connected", False

    @api.model
    def _find_for_email(self, msg_dict, server_id=None, channel_id=None):
        """The receiving channel of an email: the one read by the incoming
        server that fetched it, the one of the alias that received it, or else
        the one it was sent to."""
        channels = self.sudo().search([("channel_type", "=", "email")])
        if server_id:
            channel = channels.filtered(lambda c: c.fetchmail_server_id.id == server_id)
            if channel:
                return channel[:1]
        if channel_id:
            channel = channels.filtered(lambda c: c.id == channel_id)
            if channel:
                return channel
        recipients = set(
            email_normalize_all(
                msg_dict.get("recipients")
                or ",".join(filter(None, [msg_dict.get("to"), msg_dict.get("cc")]))
            )
        )
        return channels.filtered(
            lambda c: email_normalize(c.email_address or "") in recipients
        )[:1]

    def action_open_mail_server(self):
        """The incoming mail server of the channel, or a new one to set up."""
        self.ensure_one()
        action = {
            "type": "ir.actions.act_window",
            "res_model": "fetchmail.server",
            "view_mode": "form",
        }
        if self.fetchmail_server_id:
            action["res_id"] = self.fetchmail_server_id.id
            return action
        action["context"] = {
            "default_name": self.name,
            "default_user": self.email_address,
            SERVER_CONTEXT_KEY: True,
            CHANNEL_CONTEXT_KEY: self.id,
        }
        return action
