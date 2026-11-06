# Copyright 2026 Binhex
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import logging
from email.utils import parseaddr

from odoo import Command, api, fields, models
from odoo.tools import email_normalize, html2plaintext

from odoo.addons.mail_message_import.services.email_reader import (
    _clean_body,
    _header_lines,
    _is_decoration,
)
from odoo.addons.mail_message_import.services.tools import (
    automation_user,
    clean_text,
)

_logger = logging.getLogger(__name__)

# Prefix of the ID of the emails, to tell them from the messages of the other
# channels.
EMAIL_ID_PREFIX = "email:"
# Copy of the whole email added by an incoming server that keeps the original.
ORIGINAL_EMAIL = "original_email.eml"


class MailMessageImportMessage(models.Model):
    """An email received on a receiving channel.

    The emails arrive through the mail gateway of Odoo: the incoming mail server
    of a receiving channel creates one message per email, the email is posted
    in its chatter and its files become the files of the message. From there the
    message is identified by the address of its sender and processed as the
    messages of every channel.
    """

    _name = "mail.message.import.message"
    _inherit = ["mail.message.import.message", "mail.thread"]

    message_type = fields.Selection(
        selection_add=[("email", "Email")], ondelete={"email": "set other"}
    )
    email_subject = fields.Char(string="Subject", readonly=True)

    @api.model_create_multi
    def create(self, vals_list):
        # A received message is no document of the users: no note of its creation.
        return super(
            MailMessageImportMessage,
            self.with_context(mail_create_nolog=True, mail_create_nosubscribe=True),
        ).create(vals_list)

    @api.depends("email_subject")
    def _compute_name(self):
        res = super()._compute_name()
        for message in self.filtered(lambda m: m.message_type == "email"):
            message.name = " - ".join(
                filter(
                    None,
                    [
                        message.sender_name or message.sender_address,
                        message.email_subject,
                    ],
                )
            )
        return res

    # ------------------------------------------------------------------
    # Reception of the emails
    # ------------------------------------------------------------------

    @api.model
    def _email_routes(self, routes, fallback_model, custom_values):
        """Every email that reaches a receiving channel is a new message.

        The emails read by the incoming server of a receiving channel go to it
        even when they reply to a document of Odoo or are also sent to an
        alias. A reply to a received email is a new message too, not a note on
        the previous one: it is how corrections arrive.
        """
        if not routes:
            return routes
        if fallback_model == self._name:
            return [(self._name, False, custom_values, routes[0][3], None)]
        result = []
        for model, thread_id, values, user_id, alias in routes:
            if model == self._name and thread_id:
                previous = self.sudo().browse(thread_id)
                values = dict(values or {}, channel_id=previous.channel_id.id)
                thread_id = False
            result.append((model, thread_id, values, user_id, alias))
        return result

    @api.model
    def message_new(self, msg_dict, custom_values=None):
        """Record an email received on a receiving channel."""
        channel = self.env["mail.message.import.channel"]._find_for_email(
            msg_dict,
            server_id=self.env.context.get("default_fetchmail_server_id"),
            channel_id=(custom_values or {}).get("channel_id"),
        )
        if not channel:
            raise ValueError(
                f"The email {msg_dict.get('message_id')} was not sent to a receiving "
                "channel: link its incoming mail server to one."
            )
        return self._capture_email(channel, msg_dict)

    @api.model
    def _capture_email(self, channel, msg_dict):
        Message = self.with_user(automation_user(self.env, channel.company_id))
        message_uid = EMAIL_ID_PREFIX + (msg_dict.get("message_id") or "")
        known = (
            Message.sudo()
            .with_context(active_test=False)
            .search([("message_uid", "=", message_uid)], limit=1)
        )
        if known:
            return known
        name, address = parseaddr(msg_dict.get("email_from") or "")
        reply_to = (msg_dict.get("in_reply_to") or "").strip()
        return Message.sudo().create(
            {
                "message_uid": message_uid,
                "channel_id": channel.id,
                "company_id": channel.company_id.id,
                "sender_address": email_normalize(address)
                or clean_text(address, 256).lower(),
                "sender_name": clean_text(name, 128) or False,
                "message_type": "email",
                "email_subject": clean_text(msg_dict.get("subject"), 255) or False,
                "body": self._email_text(msg_dict) or False,
                "message_date": fields.Datetime.to_datetime(msg_dict.get("date"))
                or fields.Datetime.now(),
                "reply_to_uid": EMAIL_ID_PREFIX + reply_to if reply_to else False,
            }
        )

    @api.model
    def _email_text(self, msg_dict):
        """The headers and the text of an email, as a forwarded email is read."""
        lines = _header_lines(
            [
                ("Subject", msg_dict.get("subject")),
                ("From", msg_dict.get("email_from")),
                ("To", msg_dict.get("to")),
                ("Cc", msg_dict.get("cc")),
                ("Date", msg_dict.get("date")),
            ]
        )
        body = html2plaintext(msg_dict.get("body") or "")
        return clean_text("\n".join(lines) + "\n\n" + _clean_body(body), 20000)

    def _message_post_after_hook(self, message, msg_values):
        result = super()._message_post_after_hook(message, msg_values)
        if (
            len(self) == 1
            and self.message_type == "email"
            and not self.mail_message_id
            and message.message_type == "email"
        ):
            # The email posted by the gateway once the message was created.
            record = self.with_user(automation_user(self.env, self.company_id)).sudo()
            record._bind_email(message)
            record._route()
            _logger.info(
                "Email %s received on %s (%s)",
                record.id,
                record.channel_id.name,
                record.state,
            )
        return result

    def _bind_email(self, mail_message):
        """Keep the email and its files, without the images of the signatures
        nor the copy of the original email."""
        self.ensure_one()
        files = mail_message.attachment_ids.filtered(
            lambda a: (
                a.name != ORIGINAL_EMAIL and not _is_decoration(a.name, a.raw or b"")
            )
        )
        self.write(
            {
                "mail_message_id": mail_message.id,
                "attachment_ids": [Command.set(files.ids)],
            }
        )
