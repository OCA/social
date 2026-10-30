# Copyright 2026 Binhex
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import logging
from datetime import timedelta

from odoo import api, fields, models

from ..services.email_reader import email_type, read_email
from ..services.tools import (
    AUTOMATION_CONTEXT_KEY,
    automation_user,
    clean_text,
    commit_progress,
    truncate,
)
from .mail_message_import_message import MediaError

_logger = logging.getLogger(__name__)

# A conversation still "processing" after this delay belongs to a dead worker.
STALE_PROCESSING = timedelta(minutes=30)
# The files reach Odoo some seconds after the texts sent with them (WhatsApp
# keeps them until they are uploaded, a mailbox is read every few minutes):
# processing on request waits for them.
ARRIVAL_DELAY = timedelta(seconds=30)


class ProcessingInterrupted(Exception):
    """The processing of a conversation was interrupted by a dead worker."""


class MailMessageImportConversation(models.Model):
    """The consecutive messages of a sender, processed together.

    Messages join the open conversation of their sender. Once the sender has
    been silent for the configured minutes, the cron processes the whole
    conversation, so that clarifications and corrections are read in context.

    What processing means is left to other modules, through
    ``_process_messages``: without one, the conversation is just closed.
    """

    _name = "mail.message.import.conversation"
    _description = "Conversation"
    _order = "id desc"

    name = fields.Char(required=True, readonly=True, copy=False, default="/")
    channel_id = fields.Many2one(
        "mail.message.import.channel",
        string="Receiving channel",
        required=True,
        readonly=True,
        ondelete="restrict",
    )
    company_id = fields.Many2one("res.company", required=True, readonly=True)
    sender_id = fields.Many2one(
        "mail.message.import.sender",
        string="Sender",
        required=True,
        readonly=True,
        ondelete="restrict",
    )
    authorized_address_id = fields.Many2one(
        "mail.message.import.address", string="Authorized address", readonly=True
    )
    sender_address = fields.Char(string="Address", required=True, readonly=True)
    origin_display = fields.Char(
        string="Received by",
        compute="_compute_origin_display",
        help="The channel and the phone or email address it came from.",
    )
    message_ids = fields.One2many(
        "mail.message.import.message",
        "conversation_id",
        string="Messages",
        readonly=True,
    )
    message_count = fields.Integer(compute="_compute_counts")
    incident_ids = fields.One2many(
        "mail.message.import.incident",
        "conversation_id",
        string="Incidents",
        readonly=True,
    )
    open_incident_count = fields.Integer(compute="_compute_counts")
    state = fields.Selection(
        [
            ("open", "Waiting for messages"),
            ("processing", "Processing"),
            ("done", "Processed"),
            ("error", "Error"),
            ("cancelled", "Cancelled"),
        ],
        default="open",
        required=True,
        readonly=True,
        index=True,
    )
    first_message_date = fields.Datetime(readonly=True)
    last_message_date = fields.Datetime(readonly=True)
    process_after = fields.Datetime(readonly=True, index=True)
    process_requested = fields.Boolean(
        string="Processing requested",
        readonly=True,
        help="A person asked to process it without waiting for the inactivity.",
    )
    processing_start = fields.Datetime(readonly=True)
    processed_date = fields.Datetime(readonly=True)
    attempt_count = fields.Integer(readonly=True)
    next_attempt_date = fields.Datetime(readonly=True, index=True)
    last_error = fields.Text(readonly=True)
    processing_ref = fields.Char(
        string="Processing", readonly=True, help="Identifier of the last attempt."
    )

    def init(self):
        # A sender has a single open conversation per channel and address.
        self.env.cr.execute(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS mail_message_import_conversation_open_uniq
                ON mail_message_import_conversation
                   (channel_id, sender_address, sender_id)
             WHERE state = 'open'
            """
        )

    @api.depends(
        "channel_id.channel_type",
        "sender_address",
        "authorized_address_id.address",
        "authorized_address_id.name",
    )
    def _compute_origin_display(self):
        for conversation in self:
            conversation.origin_display = conversation.channel_id._origin_text(
                conversation.authorized_address_id, conversation.sender_address
            )

    @api.depends("message_ids", "incident_ids.state")
    def _compute_counts(self):
        for conversation in self:
            conversation.message_count = len(conversation.message_ids)
            conversation.open_incident_count = len(
                conversation.incident_ids.filtered(lambda i: i.state == "open")
            )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", "/") == "/":
                vals["name"] = self._next_name()
        return super().create(vals_list)

    @api.model
    def _next_name(self):
        return (
            self.env["ir.sequence"]
            .sudo()
            .next_by_code("mail.message.import.conversation")
            or "/"
        )

    # ------------------------------------------------------------------
    # Grouping
    # ------------------------------------------------------------------

    @api.model
    def _add_message(self, message):
        """Put ``message`` in the open conversation of its sender, or in a new
        one."""
        config = self.env["mail.message.import.config"]._get_for_company(
            message.company_id
        )
        now = fields.Datetime.now()
        process_after = now + timedelta(minutes=config.inactivity_minutes)
        self.flush_model()
        # Lock the open conversation: the cron cannot start it while it grows.
        self.env.cr.execute(
            """
            SELECT id, process_requested FROM mail_message_import_conversation
             WHERE channel_id = %s AND sender_address = %s AND sender_id = %s
               AND state = 'open'
             LIMIT 1
               FOR UPDATE
            """,
            (message.channel_id.id, message.sender_address, message.sender_id.id),
        )
        row = self.env.cr.fetchone()
        if row:
            conversation = self.sudo().browse(row[0])
            if row[1]:
                # Processing requested: only the files on their way are awaited.
                process_after = now + ARRIVAL_DELAY
            conversation.write(
                {"last_message_date": now, "process_after": process_after}
            )
        else:
            conversation = self._create_open_conversation(message, now, process_after)
        message.write({"conversation_id": conversation.id, "state": "queued"})
        self._schedule(process_after)
        return conversation

    @api.model
    def _create_open_conversation(self, message, now, process_after):
        """Open the conversation of a sender, safely against concurrent webhooks.

        Two first messages of a sender may arrive at the same time. With
        ``ON CONFLICT DO NOTHING`` the second insertion does not fail on the
        unique index: PostgreSQL raises a serialization failure instead, which
        Odoo retries, and the retry finds the conversation of the first message.
        """
        self.env.cr.execute(
            """
            INSERT INTO mail_message_import_conversation (
                name, channel_id, company_id, sender_id, authorized_address_id,
                sender_address,
                state, first_message_date, last_message_date, process_after,
                attempt_count, create_uid, create_date, write_uid, write_date
            )
            VALUES (%s, %s, %s, %s, %s, %s, 'open', %s, %s, %s, 0, %s, %s, %s, %s)
            ON CONFLICT (channel_id, sender_address, sender_id)
                WHERE state = 'open' DO NOTHING
            RETURNING id
            """,
            (
                self._next_name(),
                message.channel_id.id,
                message.company_id.id,
                message.sender_id.id,
                message.authorized_address_id.id or None,
                message.sender_address,
                now,
                now,
                process_after,
                self.env.uid,
                now,
                self.env.uid,
                now,
            ),
        )
        row = self.env.cr.fetchone()
        if not row:
            # Opened in this same transaction meanwhile.
            return self.sudo().search(
                [
                    ("channel_id", "=", message.channel_id.id),
                    ("sender_address", "=", message.sender_address),
                    ("sender_id", "=", message.sender_id.id),
                    ("state", "=", "open"),
                ],
                limit=1,
            )
        return self.sudo().browse(row[0])

    @api.model
    def _schedule(self, when):
        cron = self.env.ref(
            "mail_message_import.ir_cron_process_conversations",
            raise_if_not_found=False,
        )
        if cron:
            cron.sudo()._trigger(at=when)

    # ------------------------------------------------------------------
    # Cron
    # ------------------------------------------------------------------

    @api.model
    def _cron_process(self, limit=20):
        self._recover_stale()
        for _index in range(limit):
            conversation = self._claim_next()
            if not conversation:
                break
            # Other workers now see the conversation as taken.
            commit_progress(self.env)
            conversation._process_safely()
            commit_progress(self.env)

    @api.model
    def _recover_stale(self):
        stale = self.sudo().search(
            [
                ("state", "=", "processing"),
                ("processing_start", "<", fields.Datetime.now() - STALE_PROCESSING),
            ]
        )
        for conversation in stale:
            _logger.warning(
                "Conversation %s was interrupted, it will be retried",
                conversation.name,
            )
            conversation._register_failure(
                ProcessingInterrupted(self.env._("The processing was interrupted."))
            )

    @api.model
    def _claim_next(self):
        self.flush_model()
        now = fields.Datetime.now()
        self.env.cr.execute(
            """
            SELECT id FROM mail_message_import_conversation
             WHERE (state = 'open' AND process_after <= %(now)s)
                OR (state = 'error' AND next_attempt_date <= %(now)s)
             ORDER BY COALESCE(next_attempt_date, process_after), id
             LIMIT 1
               FOR UPDATE SKIP LOCKED
            """,
            {"now": now},
        )
        row = self.env.cr.fetchone()
        if not row:
            return self.browse()
        conversation = self.sudo().browse(row[0])._automation_env_self()
        attempt = conversation.attempt_count + 1
        conversation.write(
            {
                "state": "processing",
                "processing_start": now,
                "attempt_count": attempt,
                "next_attempt_date": False,
                "processing_ref": f"{conversation.name}#{attempt}",
            }
        )
        return conversation

    @api.model
    def _expected_errors(self):
        """The errors the processing raises on purpose, logged without their
        traceback. Each processor adds its own."""
        return (MediaError, ProcessingInterrupted)

    def _process_safely(self):
        self.ensure_one()
        try:
            with self.env.cr.savepoint():
                self._process()
        except Exception as exc:  # pylint: disable=broad-except
            if not isinstance(exc, self._expected_errors()):
                _logger.exception("Unexpected error processing %s", self.name)
            self._register_failure(exc)

    def _failure_incident_type(self, exc):
        """The type of the incident of a conversation that failed with ``exc``.
        Each processor tells it for its own errors."""
        return "processing_error"

    def _register_failure(self, exc):
        self.ensure_one()
        config = self.env["mail.message.import.config"]._get_for_company(
            self.company_id
        )
        error = truncate(str(exc) or type(exc).__name__, 2000)
        retryable = getattr(exc, "retryable", True)
        values = {"state": "error", "last_error": error, "next_attempt_date": False}
        if retryable and self.attempt_count < config.max_attempts:
            delay = timedelta(minutes=min(2**self.attempt_count, 60))
            values["next_attempt_date"] = fields.Datetime.now() + delay
            self.write(values)
            self._schedule(values["next_attempt_date"])
            return
        self.write(values)
        self.env["mail.message.import.incident"].sudo().create(
            {
                "incident_type": self._failure_incident_type(exc),
                "name": self.env._(
                    "Conversation %(conversation)s could not be processed",
                    conversation=self.name,
                ),
                "description": self.env._(
                    "%(attempts)s attempt(s) failed. Last error: %(error)s\nThe "
                    "messages are kept; retry once the cause is solved.",
                    attempts=self.attempt_count,
                    error=error,
                ),
                "conversation_id": self.id,
                "sender_id": self.sender_id.id,
                "company_id": self.company_id.id,
                "channel_id": self.channel_id.id,
            }
        )

    # ------------------------------------------------------------------
    # Processing
    # ------------------------------------------------------------------

    def _automation_env_self(self):
        company = self.company_id
        lang = company.partner_id.lang or self.env.lang or "en_US"
        return (
            self.with_user(automation_user(self.env, company))
            .sudo()
            .with_company(company)
            .with_context(lang=lang, **{AUTOMATION_CONTEXT_KEY: True})
        )

    def _process(self):
        """Get the messages of the conversation ready and process them."""
        self.ensure_one()
        conversation = self._automation_env_self()
        if not conversation.sender_id.active:
            conversation.write({"state": "cancelled", "last_error": False})
            conversation.message_ids.write({"state": "ignored"})
            return
        messages = conversation.message_ids.sorted(
            lambda m: (m.message_date or m.received_date, m.id)
        )
        messages._download_files()
        conversation._unpack_emails(messages)
        conversation._process_messages(messages)

    def _process_messages(self, messages):
        """Process ``messages``, in chronological order, with their files
        downloaded and their attached emails unpacked.

        The modules that process the conversations override it: they do their
        work and finish the conversation (``_finish``), or raise to retry it
        later. By default the conversation is finished as it is.
        """
        self.ensure_one()
        self._finish(messages)

    def _unpack_emails(self, messages):
        """Store the attachments of the forwarded emails as files of their
        message: what matters is usually in one of them.

        Done once: a file already stored is not stored again on a retry. An
        email attached to an email is unpacked too.
        """
        Attachment = self.env["ir.attachment"].sudo()
        for _depth in range(3):
            stored = False
            for message in messages:
                for attachment in message.attachment_ids:
                    data = attachment.raw or b""
                    mimetype = email_type(data, attachment.name)
                    if not mimetype:
                        continue
                    try:
                        files = read_email(data, mimetype).files
                    except Exception:  # noqa: BLE001  # pylint: disable=broad-except
                        # Left as it is, for the processor to report it.
                        continue
                    known = set(message.attachment_ids.mapped("checksum"))
                    new = [
                        file
                        for file in files
                        if Attachment._compute_checksum(file.data) not in known
                    ]
                    if not new:
                        continue
                    message.sudo().attachment_ids |= Attachment.create(
                        [
                            {
                                "name": clean_text(
                                    f"{attachment.name} / {file.name}", 255
                                ),
                                "raw": file.data,
                                "res_model": message._name,
                                "res_id": message.id,
                            }
                            for file in new
                        ]
                    )
                    stored = True
            if not stored:
                return

    def _finish(self, messages):
        messages.write({"state": "processed"})
        self.write(
            {
                "state": "done",
                "processed_date": fields.Datetime.now(),
                "last_error": False,
                "next_attempt_date": False,
            }
        )

    def _incidents_solved_by_retry(self):
        """The open incidents a retry of the conversation solves: the failures
        of its processing."""
        return self.incident_ids.filtered(
            lambda i: i.state == "open" and i.incident_type in i._retry_types()
        )

    def action_retry(self):
        """Process the conversation again with the next run of the cron."""
        conversations = self.filtered(lambda c: c.state in ("error", "cancelled"))
        now = fields.Datetime.now()
        conversations.write(
            {"state": "error", "next_attempt_date": now, "attempt_count": 0}
        )
        conversations._incidents_solved_by_retry().write(
            {
                "state": "resolved",
                "resolution_note": self.env._("Retried"),
                "resolved_by_id": self.env.uid,
                "resolved_date": now,
            }
        )
        self._schedule(now)

    def action_process_now(self):
        """Do not wait for the end of the inactivity delay, only for the files
        sent with the last messages, which arrive some seconds later."""
        now = fields.Datetime.now()
        for conversation in self.filtered(lambda c: c.state == "open"):
            when = max(now, (conversation.last_message_date or now) + ARRIVAL_DELAY)
            conversation.write({"process_requested": True, "process_after": when})
            self._schedule(when)

    def action_view_incidents(self):
        self.ensure_one()
        action = self.env["ir.actions.act_window"]._for_xml_id(
            "mail_message_import.action_mail_message_import_incident"
        )
        action["domain"] = [("conversation_id", "=", self.id)]
        if not self.open_incident_count:
            action["context"] = {}
        return action
