# Copyright 2026 Binhex
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import json
import logging

from odoo import models

_logger = logging.getLogger(__name__)

# Context key holding the Meta message being processed by the gateway, as JSON.
INBOUND_CONTEXT_KEY = "mail_message_import_inbound"


class MailGatewayWhatsappService(models.AbstractModel):
    """Record the messages that the gateway receives, without changing it.

    The gateway keeps handling the webhooks, their signature, its Discuss chats
    and the download of the files. Once it posts a message sent to a receiving
    channel, the message is recorded with a copy of its files. A message Meta
    delivers again (same ``wamid``) is skipped, so it is neither posted twice
    nor processed twice.
    """

    _inherit = "mail.gateway.whatsapp"

    def _process_update(self, chat, message, value):
        Message = self.env["mail.message.import.message"]
        wamid = message.get("id")
        if Message._is_known_uid(wamid):
            _logger.info(
                "WhatsApp message already received on gateway %s, delivery ignored",
                chat.gateway_id.id,
            )
            return None
        service = self.with_context(
            **{INBOUND_CONTEXT_KEY: json.dumps({"message": message, "value": value})}
        )
        result = super(MailGatewayWhatsappService, service)._process_update(
            chat, message, value
        )
        if wamid and not Message._is_known_uid(wamid):
            # The gateway posts nothing for some messages (reactions...).
            Message._capture_inbound(chat.gateway_id, chat, message, value, None)
        return result

    def _post_process_message(self, message, channel):
        result = super()._post_process_message(message, channel)
        inbound = self.env.context.get(INBOUND_CONTEXT_KEY)
        if inbound:
            data = json.loads(inbound)
            Message = self.env["mail.message.import.message"]
            if not Message._is_known_uid(data["message"].get("id")):
                Message._capture_inbound(
                    channel.gateway_id, channel, data["message"], data["value"], message
                )
        return result
