# Copyright 2026 Binhex
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import json
import os
import re
from datetime import datetime, timezone

from odoo import api, fields, models

from odoo.addons.mail_message_import.services.tools import clean_text, truncate


class MailMessageImportMessage(models.Model):
    """A message received by WhatsApp, as Meta delivers it to the gateway.

    The gateway posts the message in its Discuss chat; this record keeps,
    beside it, what the module needs: the Meta identifier (``wamid``) as the
    message ID, the phone of the sender and a copy of its files.
    """

    _inherit = "mail.message.import.message"

    message_type = fields.Selection(
        selection_add=[
            ("location", "Location"),
            ("contacts", "Contacts"),
            ("interactive", "Interactive"),
            ("button", "Button"),
            ("sticker", "Sticker"),
            ("reaction", "Reaction"),
        ],
        ondelete={
            "location": "set other",
            "contacts": "set other",
            "interactive": "set other",
            "button": "set other",
            "sticker": "set other",
            "reaction": "set other",
        },
    )
    discuss_channel_id = fields.Many2one(
        "discuss.channel", string="Discuss chat", readonly=True, ondelete="set null"
    )

    @api.model
    def _ignored_types(self):
        return super()._ignored_types() | {"sticker", "reaction"}

    # ------------------------------------------------------------------
    # Capture of the webhooks
    # ------------------------------------------------------------------

    @api.model
    def _capture_inbound(self, gateway, chat, message, value, mail_message):
        """Record a message of Meta handled by the gateway.

        :param message: the message of the webhook, as sent by Meta.
        :param value: the ``value`` of the change that contains it.
        :param mail_message: the message posted by the gateway in ``chat``, if
            any: some messages (reactions...) are not posted.
        """
        wamid = message.get("id")
        if not wamid:
            return self.browse()
        channel = self.env["mail.message.import.channel"]._find_for_update(
            gateway, value
        )
        if not channel:
            return self.browse()
        sender = re.sub(r"\D", "", str(message.get("from") or ""))
        message_type = message.get("type") or "other"
        if message_type not in dict(self._fields["message_type"].selection):
            message_type = "other"
        record = self._receive_message(
            channel,
            {
                "message_uid": wamid,
                "discuss_channel_id": chat.id if chat else False,
                "mail_message_id": mail_message.id if mail_message else False,
                "sender_address": f"+{sender}" if sender else False,
                "sender_name": self._sender_name(value, sender),
                "message_type": message_type,
                "body": self._message_text(message),
                "message_date": self._message_date(message),
                "reply_to_uid": (message.get("context") or {}).get("id"),
                "raw_payload": truncate(
                    json.dumps(message, indent=1, ensure_ascii=False), 20000
                ),
            },
        )
        record._copy_attachments(message, mail_message)
        return record

    @api.model
    def _sender_name(self, value, sender):
        for contact in value.get("contacts") or []:
            if str(contact.get("wa_id")) == sender:
                return clean_text((contact.get("profile") or {}).get("name"), 128)
        return False

    @api.model
    def _message_date(self, message):
        try:
            timestamp = int(message.get("timestamp"))
        except (TypeError, ValueError):
            return fields.Datetime.now()
        return datetime.fromtimestamp(timestamp, tz=timezone.utc).replace(tzinfo=None)

    @api.model
    def _message_text(self, message):
        """The text written by the sender, whatever the kind of message."""
        texts = [(message.get("text") or {}).get("body")]
        for key in ("image", "document", "video", "audio"):
            texts.append((message.get(key) or {}).get("caption"))
        button = message.get("button") or {}
        texts.append(button.get("text"))
        interactive = message.get("interactive") or {}
        for key in ("button_reply", "list_reply"):
            reply = interactive.get(key) or {}
            texts += [reply.get("title"), reply.get("description")]
        location = message.get("location")
        if location:
            texts.append(
                " ".join(
                    str(location.get(key) or "")
                    for key in ("name", "address", "latitude", "longitude")
                ).strip()
            )
        for contact in message.get("contacts") or []:
            name = (contact.get("name") or {}).get("formatted_name")
            phones = ", ".join(p.get("phone", "") for p in contact.get("phones") or [])
            texts.append(f"{name or ''} {phones}".strip())
        return "\n".join(clean_text(text, 20000) for text in texts if text) or False

    def _copy_attachments(self, message, mail_message):
        """Keep a copy of the files bound to this record and its access rules."""
        self.ensure_one()
        attachments = mail_message.attachment_ids if mail_message else []
        if not attachments:
            return
        filename = os.path.basename(
            (message.get("document") or {}).get("filename") or ""
        )
        copies = self.env["ir.attachment"]
        for attachment in attachments:
            values = {"res_model": self._name, "res_id": self.id}
            if filename and len(attachments) == 1:
                values["name"] = clean_text(filename, 255)
            copies |= attachment.sudo().copy(values)
        self.attachment_ids |= copies
