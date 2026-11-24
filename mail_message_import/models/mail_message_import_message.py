# Copyright 2026 Binhex
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import logging

from odoo import _, api, fields, models

from ..services.tools import automation_user, clean_text

_logger = logging.getLogger(__name__)

# The kinds of message of every channel; each channel adds its own.
MESSAGE_TYPES = [
    ("text", "Text"),
    ("image", "Image"),
    ("document", "Document"),
    ("audio", "Audio"),
    ("video", "Video"),
    ("other", "Other"),
]


class MediaError(Exception):
    """The files of a message could not be downloaded from its channel."""

    def __init__(self, message, retryable=True):
        super().__init__(message)
        self.retryable = retryable


class MailMessageImportMessage(models.Model):
    """A message received on a receiving channel, by any channel type.

    Each channel module turns what it receives into one of these records: the
    identifier of the message in its channel (``message_uid``, unique), the
    address of the sender, the text and a copy of the files, bound to this
    record. From there the message is identified and processed the same way
    whatever its channel.
    """

    _name = "mail.message.import.message"
    _description = "Received Message"
    _order = "message_date desc, id desc"

    name = fields.Char(compute="_compute_name")
    message_uid = fields.Char(
        string="Message ID",
        required=True,
        readonly=True,
        index=True,
        help="Identifier of the message in its channel.",
    )
    channel_id = fields.Many2one(
        "mail.message.import.channel",
        string="Receiving channel",
        required=True,
        readonly=True,
        ondelete="restrict",
        index=True,
    )
    channel_type = fields.Selection(related="channel_id.channel_type", store=True)
    company_id = fields.Many2one("res.company", required=True, readonly=True)
    mail_message_id = fields.Many2one(
        "mail.message", string="Posted message", readonly=True, ondelete="set null"
    )
    sender_id = fields.Many2one(
        "mail.message.import.sender",
        string="Sender",
        readonly=True,
        index=True,
        ondelete="restrict",
    )
    authorized_address_id = fields.Many2one(
        "mail.message.import.address", string="Authorized address", readonly=True
    )
    sender_address = fields.Char(
        string="Address",
        readonly=True,
        index=True,
        help="Address that sent the message: the phone for WhatsApp, the email "
        "address for email...",
    )
    sender_name = fields.Char(string="Sender name", readonly=True)
    origin_display = fields.Char(
        string="Received by",
        compute="_compute_origin_display",
        help="The channel and the phone or email address it came from.",
    )
    message_type = fields.Selection(MESSAGE_TYPES, string="Type", readonly=True)
    body = fields.Text(string="Text", readonly=True)
    attachment_ids = fields.Many2many(
        "ir.attachment",
        "mail_message_import_message_attachment_rel",
        "message_id",
        "attachment_id",
        string="Files",
        readonly=True,
    )
    attachment_count = fields.Integer(
        string="Number of files", compute="_compute_attachment_count"
    )
    media_pending = fields.Boolean(
        string="Files to download",
        readonly=True,
        help="Its files stay in its channel until the conversation is processed.",
    )
    message_date = fields.Datetime(string="Sent on", readonly=True)
    received_date = fields.Datetime(
        string="Received on", default=fields.Datetime.now, readonly=True
    )
    reply_to_uid = fields.Char(
        string="Reply to",
        readonly=True,
        help="Identifier of the message it replies to, in its channel.",
    )
    conversation_id = fields.Many2one(
        "mail.message.import.conversation",
        string="Conversation",
        readonly=True,
        index=True,
    )
    state = fields.Selection(
        [
            ("unidentified", "Unidentified sender"),
            ("queued", "Waiting"),
            ("processed", "Processed"),
            ("ignored", "Ignored"),
        ],
        default="queued",
        required=True,
        readonly=True,
        index=True,
    )
    note = fields.Text(readonly=True)
    raw_payload = fields.Text(
        string="Original data",
        readonly=True,
        help="The message as its channel delivered it.",
    )

    _sql_constraints = [
        (
            "message_uid_uniq",
            "unique(message_uid)",
            "This message was already received.",
        ),
    ]

    @api.depends("sender_name", "sender_address", "message_type", "message_date")
    def _compute_name(self):
        types = dict(self._fields["message_type"]._description_selection(self.env))
        for message in self:
            sender = message.sender_name or message.sender_address
            message.name = f"{sender} - {types.get(message.message_type, '')}"

    @api.depends("attachment_ids")
    def _compute_attachment_count(self):
        for message in self:
            message.attachment_count = len(message.attachment_ids)

    @api.depends(
        "channel_id.channel_type",
        "sender_address",
        "authorized_address_id.address",
        "authorized_address_id.name",
    )
    def _compute_origin_display(self):
        for message in self:
            message.origin_display = message.channel_id._origin_text(
                message.authorized_address_id, message.sender_address
            )

    # ------------------------------------------------------------------
    # Reception
    # ------------------------------------------------------------------

    @api.model
    def _is_known_uid(self, message_uid):
        return bool(message_uid) and bool(
            self.sudo()
            .with_context(active_test=False)
            .search_count([("message_uid", "=", message_uid)], limit=1)
        )

    @api.model
    def _receive_message(self, channel, values, files=None):
        """Record a message received on ``channel`` and identify its sender.

        The entry point of the channel modules: each one turns what it
        receives into ``values`` (``message_uid``, unique in all the channels,
        and as much as it knows of ``sender_address``, ``sender_name``,
        ``message_type``, ``body``, ``message_date``, ``reply_to_uid``...) and
        the files it already has into ``files``, dicts with ``name``, ``raw``
        and ``mimetype``.
        """
        # Recorded by the agent of the module when the channel receives as OdooBot.
        Message = self.with_user(automation_user(self.env, channel.company_id))
        record = Message.sudo().create(
            {
                "channel_id": channel.id,
                "company_id": channel.company_id.id,
                **values,
            }
        )
        record._store_files(files or [])
        record._route()
        _logger.info(
            "Message %s received on %s (%s)",
            record.id,
            channel.name,
            record.state,
        )
        return record

    def _store_files(self, files):
        """Keep the files of the message, bound to this record."""
        self.ensure_one()
        if not files:
            return
        self.attachment_ids |= (
            self.env["ir.attachment"]
            .sudo()
            .create(
                [
                    {
                        "name": clean_text(file["name"], 255) or "file",
                        "raw": file["raw"],
                        "mimetype": file.get("mimetype"),
                        "res_model": self._name,
                        "res_id": self.id,
                    }
                    for file in files
                ]
            )
        )

    def _download_files(self):
        """Download the files that stayed in the channel (``media_pending``),
        when the conversation is processed. Each channel that leaves them there
        downloads its own, and raises ``MediaError`` when it cannot."""
        for message in self.filtered("media_pending"):
            raise MediaError(
                _(
                    "The files of the message %(message)s cannot be downloaded: "
                    "its channel is not installed.",
                    message=message.id,
                ),
                retryable=False,
            )

    @api.model
    def _ignored_types(self):
        """Kinds of message that are not processed."""
        return {"other"}

    def _route(self):
        """Identify the sender of the message and queue it for processing."""
        self.ensure_one()
        if self.message_type in self._ignored_types():
            self.state = "ignored"
            return
        addresses = self.env["mail.message.import.address"]._find_for_sender(
            self.channel_id, self.sender_address
        )
        if len(addresses) > 1:
            self.write(
                {
                    "state": "unidentified",
                    "note": _(
                        "The address is authorized for several senders: %(senders)s.",
                        senders=", ".join(addresses.sender_id.mapped("name")),
                    ),
                }
            )
            return
        if addresses:
            self._link_sender(addresses.sender_id, addresses)
            self.env["mail.message.import.conversation"]._add_message(self)
            return
        self.state = "unidentified"

    def _link_sender(self, sender, address=None):
        self.write(
            {
                "sender_id": sender.id,
                "authorized_address_id": address.id if address else False,
                "company_id": sender.company_id.id,
            }
        )

    def action_view_attachments(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Files"),
            "res_model": "ir.attachment",
            "view_mode": "kanban,tree,form",
            "domain": [("id", "in", self.attachment_ids.ids)],
            "context": {"create": False},
        }

    def action_view_conversation(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "res_model": "mail.message.import.conversation",
            "res_id": self.conversation_id.id,
            "view_mode": "form",
        }

    def action_assign_sender(self):
        return {
            "type": "ir.actions.act_window",
            "name": _("Assign to a sender"),
            "res_model": "mail.message.import.assign.sender",
            "view_mode": "form",
            "target": "new",
            "context": {"default_message_ids": self.ids},
        }
