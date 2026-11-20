# Copyright 2026 Grupo Isonor - David Palanca
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from datetime import datetime

from odoo import models


class MailGatewayWhatsappService(models.AbstractModel):
    _inherit = "mail.gateway.whatsapp"

    def _receive_update(self, gateway, update):
        result = super()._receive_update(gateway, update)
        for entry in (update or {}).get("entry", []):
            for change in entry.get("changes", []):
                if change.get("field") == "smb_message_echoes":
                    self._receive_message_echoes(gateway, change.get("value", {}))
        return result

    def _receive_message_echoes(self, gateway, value):
        """Process the messages sent to the customer outside Odoo.

        Meta pushes them on the ``smb_message_echoes`` field when the number is
        also used from the WhatsApp Business app. On an echo, ``from`` is the
        business number and ``to`` the customer one.
        """
        for message in value.get("message_echoes", []):
            if self._get_echo_notification(gateway, message["id"]):
                # Meta also echoes the messages we send through the API and it
                # can redeliver the same webhook more than once.
                continue
            chat = self._get_channel(gateway, message["to"], value, force_create=True)
            if not chat:
                continue
            self._process_echo(chat, message, value)

    def _get_echo_notification(self, gateway, gateway_message_id):
        return (
            self.env["mail.notification"]
            .sudo()
            .search(
                [
                    ("gateway_message_id", "=", gateway_message_id),
                    ("gateway_channel_id.gateway_id", "=", gateway.id),
                ],
                limit=1,
            )
        )

    def _get_echo_author(self, gateway, message, value):
        # Meta does not tell which agent wrote from the WhatsApp Business app.
        return gateway.company_id.partner_id

    def _process_echo(self, chat, message, value):
        chat.ensure_one()
        body, attachments = self._get_message_content(chat, message)
        if not body and not attachments:
            return False
        author = self._get_echo_author(chat.gateway_id, message, value)
        # Meta already delivered the message, it must never be sent again
        new_message = (
            chat.sudo()
            .with_context(no_gateway_notification=True)
            .message_post(
                body=body,
                author_id=author.id,
                gateway_type="whatsapp",
                date=datetime.fromtimestamp(int(message["timestamp"])),
                subtype_xmlid="mail.mt_comment",
                message_type="comment",
                attachments=attachments,
            )
        )
        self.env["mail.notification"].sudo().create(
            {
                "mail_message_id": new_message.id,
                "gateway_channel_id": chat.id,
                "notification_type": "gateway",
                "gateway_type": "whatsapp",
                "notification_status": "sent",
                "gateway_message_id": message["id"],
            }
        )
        self._post_process_message(new_message, chat)
        return new_message

    def _get_author(self, gateway, update):
        echoes = update.get("message_echoes")
        if echoes:
            # On an echo we are the sender, so the counterpart is the recipient
            update = dict(update, messages=[{"from": echoes[0].get("to")}])
        return super()._get_author(gateway, update)

    def _get_author_vals(self, gateway, author_id, update):
        result = super()._get_author_vals(gateway, author_id, update)
        if not result and update.get("message_echoes"):
            # Echo payloads carry no contact profile
            result = {
                "name": str(author_id),
                "gateway_id": gateway.id,
                "gateway_token": str(author_id),
            }
        return result

    def _get_channel_vals(self, gateway, token, update):
        result = super()._get_channel_vals(gateway, token, update)
        if not result.get("name"):
            author = self._get_author(gateway, update)
            result["name"] = author.name if author else token
        return result
