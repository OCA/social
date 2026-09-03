# Copyright 2024 Dixmit
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
import hashlib
import hmac
import logging
import mimetypes
import traceback
from datetime import datetime
from io import StringIO

import requests
import requests_toolbelt

from odoo import models
from odoo.exceptions import UserError
from odoo.http import request
from odoo.tools import html2plaintext

from odoo.addons.base.models.ir_mail_server import MailDeliveryException

_logger = logging.getLogger(__name__)


class MailGatewayWhatsappService(models.AbstractModel):
    _inherit = "mail.gateway.abstract"
    _name = "mail.gateway.whatsapp"
    _description = "Whatsapp Gateway services"

    def _receive_get_update(self, bot_data, req, **kwargs):
        self._verify_update(bot_data, {})
        gateway = self.env["mail.gateway"].browse(bot_data["id"])
        if kwargs.get("hub.verify_token") != gateway.whatsapp_security_key:
            return None
        gateway.sudo().integrated_webhook_state = "integrated"
        response = request.make_response(kwargs.get("hub.challenge"))
        response.status_code = 200
        return response

    def _set_webhook(self, gateway):
        gateway.integrated_webhook_state = "pending"

    def _verify_update(self, bot_data, kwargs):
        signature = request.httprequest.headers.get("x-hub-signature-256")
        if not signature:
            return False
        hex_dig = hmac.new(
            bot_data["webhook_secret"].encode(),
            request.httprequest.data,
            hashlib.sha256,
        ).hexdigest()
        return f"sha256={hex_dig}" == signature

    def _get_channel_vals(self, gateway, token, update):
        result = super()._get_channel_vals(gateway, token, update)
        for contact in update.get("contacts", []):
            if contact["wa_id"] == token:
                result["name"] = contact["profile"]["name"]
                continue
        if not result.get("name"):
            # Echo payloads carry no contact profile
            author = self._get_author(gateway, update)
            result["name"] = author.name if author else token
        return result

    def _receive_update(self, gateway, update):
        if not update:
            return
        for entry in update.get("entry", []):
            for change in entry.get("changes", []):
                field = change.get("field")
                if field == "messages":
                    self._receive_messages(gateway, change.get("value", {}))
                elif field == "smb_message_echoes":
                    self._receive_message_echoes(gateway, change.get("value", {}))

    def _receive_messages(self, gateway, value):
        for message in value.get("messages", []):
            chat = self._get_channel(gateway, message["from"], value, force_create=True)
            if not chat:
                continue
            self._process_update(chat, message, value)
        for status_info in value.get("statuses", []):
            chat_id = gateway._get_channel_id(status_info["recipient_id"])
            if status_info.get("status", "") != "failed" or not chat_id:
                continue
            self._process_update_status(chat_id, status_info)

    def _receive_message_echoes(self, gateway, value):
        """Process messages sent to the customer outside Odoo.

        Meta pushes them on the ``smb_message_echoes`` field when the number is
        also used from the WhatsApp Business app. On an echo, ``from`` is the
        business number and ``to`` the customer one.
        """
        for message in value.get("message_echoes", []):
            if self._get_gateway_notification(gateway, message["id"]):
                # Echoes are also sent for messages we posted through the API,
                # and Meta may redeliver the same webhook more than once.
                continue
            chat = self._get_channel(gateway, message["to"], value, force_create=True)
            if not chat:
                continue
            self._process_echo(chat, message, value)

    def _get_gateway_notification(self, gateway, gateway_message_id):
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
        # The message was already delivered by Meta, never send it back
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

    def _process_update_status(self, chat_id, status_info):
        notification = (
            self.env["mail.notification"]
            .sudo()
            .search(
                [
                    ("gateway_message_id", "=", status_info["id"]),
                    ("gateway_channel_id", "=", chat_id),
                ]
            )
        )
        if not notification:
            return
        errors = [
            f"[{error['code']}] {error['error_data']['details']}"
            for error in status_info.get("errors", [])
        ]
        notification.write(
            {
                "failure_type": "unknown",
                "notification_status": "exception",
                "failure_reason": "\n".join(errors),
            }
        )
        # notify user that we have a failure
        notification.mail_message_id._notify_message_notification_update()

    def _get_message_content(self, chat, message):
        body = ""
        attachments = []
        if message.get("text"):
            body = message.get("text").get("body")
        for key in ["image", "audio", "video", "document", "sticker"]:
            if message.get(key):
                image_id = message.get(key).get("id")
                if image_id:
                    image_info_request = requests.get(
                        f"https://graph.facebook.com/"
                        f"v{chat.gateway_id.whatsapp_version}/{image_id}",
                        headers={
                            "Authorization": f"Bearer {chat.gateway_id.token}",
                        },
                        timeout=10,
                        proxies=self._get_proxies(),
                    )
                    image_info_request.raise_for_status()
                    image_info = image_info_request.json()
                    image_url = image_info["url"]
                else:
                    image_url = message.get(key).get("url")
                if not image_url:
                    continue
                image_request = requests.get(
                    image_url,
                    headers={
                        "Authorization": f"Bearer {chat.gateway_id.token}",
                    },
                    timeout=10,
                    proxies=self._get_proxies(),
                )
                image_request.raise_for_status()
                attachment_info = {}
                if "audio/" in image_info["mime_type"]:
                    # Tell discuss to treat this attachment as voice.
                    attachment_info["voice"] = True
                body += message.get(key).get("caption", "")
                attachments.append(
                    (
                        "{}{}".format(
                            image_id,
                            mimetypes.guess_extension(image_info["mime_type"]),
                        ),
                        image_request.content,
                        attachment_info,
                    )
                )
        if message.get("location"):
            body += (
                '<a target="_blank" href="https://www.google.com/'
                f'maps/search/?api=1&query={message["location"]["latitude"]},'
                f'{message["location"]["longitude"]}">Location</a>'
            )
        if message.get("contacts"):
            pass
        return body, attachments

    def _process_update(self, chat, message, value):
        chat.ensure_one()
        body, attachments = self._get_message_content(chat, message)
        if len(body) > 0 or attachments:
            author = self._get_author(chat.gateway_id, value)
            if author._name == "mail.guest":
                chat = chat.with_user(self.env.ref("base.public_user").id).with_context(
                    guest=author
                )
            # TODO: Check the sudo...
            new_message = chat.sudo().message_post(
                body=body,
                author_id=author and author._name == "res.partner" and author.id,
                gateway_type="whatsapp",
                date=datetime.fromtimestamp(int(message["timestamp"])),
                # message_id=update.message.message_id,
                subtype_xmlid="mail.mt_comment",
                message_type="comment",
                attachments=attachments,
            )
            self._post_process_message(new_message, chat)
            related_message_id = message.get("context", {}).get("id", False)
            if related_message_id:
                related_message = (
                    self.env["mail.notification"]
                    .search(
                        [
                            ("gateway_channel_id", "=", chat.id),
                            ("gateway_message_id", "=", related_message_id),
                        ]
                    )
                    .mail_message_id
                )
                new_message.parent_id = related_message.id
                if related_message and related_message.gateway_message_id:
                    new_related_message = (
                        self.env[related_message.gateway_message_id.model]
                        .browse(related_message.gateway_message_id.res_id)
                        .message_post(
                            body=body,
                            author_id=author
                            and author._name == "res.partner"
                            and author.id,
                            gateway_type="whatsapp",
                            date=datetime.fromtimestamp(int(message["timestamp"])),
                            # message_id=update.message.message_id,
                            subtype_xmlid="mail.mt_comment",
                            message_type="comment",
                            attachments=attachments,
                        )
                    )
                    self._post_process_reply(related_message)
                    new_message.gateway_message_id = new_related_message
                    gateway_thread_data = new_message.sudo().gateway_thread_data
                    new_message._bus_send_store(
                        new_message,
                        {
                            "gateway_thread_data": gateway_thread_data,
                        },
                    )

    def _send(
        self,
        gateway,
        record,
        auto_commit=False,
        raise_exception=False,
        parse_mode=False,
    ):
        message = False
        try:
            attachment_mimetype_map = self._get_whatsapp_mimetype_kind()
            for attachment in record.mail_message_id.attachment_ids:
                if attachment.mimetype not in attachment_mimetype_map:
                    raise UserError(self.env._("Mimetype is not valid"))
                attachment_type = attachment_mimetype_map[attachment.mimetype]
                m = requests_toolbelt.multipart.encoder.MultipartEncoder(
                    fields={
                        "file": (
                            attachment.name,
                            attachment.raw,
                            attachment.mimetype,
                        ),
                        "messaging_product": "whatsapp",
                        # "type": attachment_type
                    },
                )

                response = requests.post(
                    f"https://graph.facebook.com/"
                    f"v{gateway.whatsapp_version}/{gateway.whatsapp_from_phone}/media",
                    headers={
                        "Authorization": f"Bearer {gateway.token}",
                        "content-type": m.content_type,
                    },
                    data=m,
                    timeout=10,
                    proxies=self._get_proxies(),
                )
                response.raise_for_status()
                response = requests.post(
                    f"https://graph.facebook.com/"
                    f"v{gateway.whatsapp_version}/{gateway.whatsapp_from_phone}/messages",
                    headers={"Authorization": f"Bearer {gateway.token}"},
                    json=self._send_payload(
                        record.gateway_channel_id,
                        media_id=response.json()["id"],
                        media_type=attachment_type,
                        media_name=attachment.name,
                    ),
                    timeout=10,
                    proxies=self._get_proxies(),
                )
                response.raise_for_status()
                message = response.json()
            body = self._get_message_body(record)
            if body:
                response = requests.post(
                    f"https://graph.facebook.com/"
                    f"v{gateway.whatsapp_version}/{gateway.whatsapp_from_phone}/messages",
                    headers={"Authorization": f"Bearer {gateway.token}"},
                    json=self._send_payload(record.gateway_channel_id, body=body),
                    timeout=10,
                    proxies=self._get_proxies(),
                )
                response.raise_for_status()
                message = response.json()
        except Exception as exc:
            buff = StringIO()
            traceback.print_exc(file=buff)
            _logger.error(buff.getvalue())
            if raise_exception:
                raise MailDeliveryException(
                    self.env._("Unable to send the whatsapp message")
                ) from exc
            else:
                _logger.warning(f"Issue sending message with id {record.id}: {exc}")
                record.sudo().write(
                    {
                        "notification_status": "exception",
                        "failure_reason": exc,
                        "failure_type": "unknown",
                    }
                )
        if message:
            record.sudo().write(
                {
                    "notification_status": "sent",
                    "failure_reason": False,
                    "gateway_message_id": message["messages"][0]["id"],
                }
            )
        if auto_commit is True:
            # pylint: disable=invalid-commit
            self.env.cr.commit()

    def _send_payload(
        self, channel, body=False, media_id=False, media_type=False, media_name=False
    ):
        whatsapp_template = self.env["mail.whatsapp.template"]
        if self.env.context.get("whatsapp_template_id"):
            whatsapp_template = self.env["mail.whatsapp.template"].browse(
                self.env.context.get("whatsapp_template_id")
            )
        if body:
            payload = {
                "messaging_product": "whatsapp",
                "recipient_type": "individual",
                "to": channel.gateway_channel_token,
            }
            if whatsapp_template:
                payload.update(
                    {
                        "type": "template",
                        "template": {
                            "name": whatsapp_template.template_name,
                            "language": {"code": whatsapp_template.language},
                            "components": whatsapp_template.prepare_value_to_send(),
                        },
                    }
                )
            else:
                payload.update(
                    {
                        "type": "text",
                        "text": {"preview_url": False, "body": html2plaintext(body)},
                    }
                )
            return payload
        if media_id:
            media_data = {"id": media_id}
            if media_type == "document":
                media_data["filename"] = media_name
            return {
                "messaging_product": "whatsapp",
                "recipient_type": "individual",
                "to": channel.gateway_channel_token,
                "type": media_type,
                media_type: media_data,
            }

    def _get_whatsapp_mimetype_kind(self):
        return {
            "text/plain": "document",
            "application/pdf": "document",
            "application/vnd.ms-powerpoint": "document",
            "application/msword": "document",
            "application/vnd.ms-excel": "document",
            "application/vnd.openxmlformats-officedocument."
            "wordprocessingml.document": "document",
            "application/vnd.openxmlformats-officedocument."
            "presentationml.presentation": "document",
            "application/vnd.openxmlformats-officedocument."
            "spreadsheetml.sheet": "document",
            "audio/aac": "audio",
            "audio/mp4": "audio",
            "audio/mpeg": "audio",
            "audio/amr": "audio",
            "audio/ogg": "audio",
            "image/jpeg": "image",
            "image/png": "image",
            "video/mp4": "video",
            "video/3gp": "video",
            "image/webp": "sticker",
        }

    def _get_author_token(self, update):
        for message in update.get("messages") or []:
            return message.get("from")
        for message in update.get("message_echoes") or []:
            # On an echo we are the sender, the counterpart is the recipient
            return message.get("to")
        return False

    def _get_author(self, gateway, update):
        author_id = self._get_author_token(update)
        if author_id:
            gateway_partner = self.env["res.partner.gateway.channel"].search(
                [
                    ("gateway_id", "=", gateway.id),
                    ("gateway_token", "=", str(author_id)),
                ],
                limit=1,
            )
            if gateway_partner:
                return gateway_partner.partner_id
            partner = self.env["res.partner"].search(
                [("phone_sanitized", "=", "+" + str(author_id))], limit=1
            )
            if partner:
                self.env["res.partner.gateway.channel"].create(
                    {
                        "name": gateway.name,
                        "partner_id": partner.id,
                        "gateway_id": gateway.id,
                        "gateway_token": str(author_id),
                    }
                )
                return partner
            guest = self.env["mail.guest"].search(
                [
                    ("gateway_id", "=", gateway.id),
                    ("gateway_token", "=", str(author_id)),
                ],
                limit=1,
            )
            if guest:
                return guest
            author_vals = self._get_author_vals(gateway, author_id, update)
            if author_vals:
                return self.env["mail.guest"].create(author_vals)

        return False

    def _get_author_vals(self, gateway, author_id, update):
        for contact in update.get("contacts", []):
            if contact["wa_id"] == author_id:
                return {
                    "name": contact.get("profile", {}).get("name", "Anonymous"),
                    "gateway_id": gateway.id,
                    "gateway_token": str(author_id),
                }
        if update.get("message_echoes"):
            # Echo payloads carry no contact profile
            return {
                "name": str(author_id),
                "gateway_id": gateway.id,
                "gateway_token": str(author_id),
            }

    def _get_proxies(self):
        # This hook has been created in order to add a proxy if needed.
        # By default, it does nothing.
        return {}
