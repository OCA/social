# Copyright 2018 ACSONE SA/NV
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).
import hashlib
import hmac
import logging
import mimetypes
import traceback
from datetime import datetime
from io import StringIO

import requests
import requests_toolbelt

from odoo import _, models
from odoo.exceptions import UserError
from odoo.http import request
from odoo.tools import html2plaintext

from odoo.addons.base.models.ir_mail_server import MailDeliveryException

_logger = logging.getLogger(__name__)


class MailBrokerWhatsappService(models.AbstractModel):
    _inherit = "mail.broker.abstract"
    _name = "mail.broker.whatsapp"
    _description = "Whatsapp Broker services"

    def _receive_get_update(self, bot_data, req, **kwargs):
        self._verify_update(bot_data, {})
        broker = self.env["mail.broker"].browse(bot_data["id"])
        if kwargs.get("hub.verify_token") != broker.whatsapp_security_key:
            return None
        broker.sudo().integrated_webhook_state = "integrated"
        response = request.make_response(kwargs.get("hub.challenge"))
        response.status_code = 200
        return response

    def _set_webhook(self, broker):
        broker.integrated_webhook_state = "pending"

    def _verify_update(self, bot_data, kwargs):
        signature = request.httprequest.headers.get("x-hub-signature-256")
        if not signature:
            return False
        if (
            "sha256=%s"
            % hmac.new(
                bot_data["webhook_secret"].encode(),
                request.httprequest.data,
                hashlib.sha256,
            ).hexdigest()
            != signature
        ):
            return False
        return True

    def _get_channel_vals(self, broker, token, update):
        result = super()._get_channel_vals(broker, token, update)
        for contact in update.get("contacts", []):
            if contact["wa_id"] == token:
                result["name"] = contact["profile"]["name"]
                continue
        return result

    def _receive_update(self, broker, update):
        if update:
            for entry in update["entry"]:
                for change in entry["changes"]:
                    if change["field"] != "messages":
                        continue
                    for message in change["value"].get("messages", []):
                        chat = self._get_channel(
                            broker, message["from"], change["value"], force_create=True
                        )
                        if not chat:
                            continue
                        self._process_update(chat, message, change["value"])

    def _process_update(self, chat, message, value):
        chat.ensure_one()
        body = ""
        attachments = []
        if message.get("text"):
            body = message.get("text").get("body")
        for key in ["image", "audio", "video", "document", "sticker"]:
            if message.get(key):
                image_id = message.get(key).get("id")
                if image_id:
                    image_info_request = requests.get(
                        "https://graph.facebook.com/v%s/%s"
                        % (
                            chat.broker_id.whatsapp_version,
                            image_id,
                        ),
                        headers={
                            "Authorization": "Bearer %s" % chat.broker_id.token,
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
                        "Authorization": "Bearer %s" % chat.broker_id.token,
                    },
                    timeout=10,
                    proxies=self._get_proxies(),
                )
                image_request.raise_for_status()
                attachments.append(
                    (
                        "{}{}".format(
                            image_id,
                            mimetypes.guess_extension(image_info["mime_type"]),
                        ),
                        image_request.content,
                    )
                )
        if message.get("location"):
            body += (
                '<a target="_blank" href="https://www.google.com/'
                'maps/search/?api=1&query=%s,%s">Location</a>'
                % (
                    message["location"]["latitude"],
                    message["location"]["longitude"],
                )
            )
        if message.get("contacts"):
            pass
        if len(body) > 0 or attachments:
            author = self._get_author(chat.broker_id, value)
            new_message = chat.message_post(
                body=body,
                author_id=author and author._name == "res.partner" and author.id,
                broker_type="whatsapp",
                date=datetime.fromtimestamp(int(message["timestamp"])),
                # message_id=update.message.message_id,
                subtype_xmlid="mail.mt_comment",
                message_type="comment",
                attachments=attachments,
            )
            related_message_id = message.get("context", {}).get("id", False)
            if related_message_id:
                related_message = (
                    self.env["mail.notification"]
                    .search(
                        [
                            ("broker_channel_id", "=", chat.id),
                            ("broker_message_id", "=", related_message_id),
                        ]
                    )
                    .mail_message_id
                )
                if related_message and related_message.broker_message_id:
                    new_related_message = (
                        self.env[related_message.broker_message_id.model]
                        .browse(related_message.broker_message_id.res_id)
                        .message_post(
                            body=body,
                            author_id=author
                            and author._name == "res.partner"
                            and author.id,
                            broker_type="whatsapp",
                            date=datetime.fromtimestamp(int(message["timestamp"])),
                            # message_id=update.message.message_id,
                            subtype_xmlid="mail.mt_comment",
                            message_type="comment",
                            attachments=attachments,
                        )
                    )
                    new_message.broker_message_id = new_related_message

    def _send(
        self, broker, record, auto_commit=False, raise_exception=False, parse_mode=False
    ):
        message = False
        try:
            attachment_mimetype_map = self._get_whatsapp_mimetype_kind()
            for attachment in record.mail_message_id.attachment_ids:
                if attachment.mimetype not in attachment_mimetype_map:
                    raise UserError(_("Mimetype is not valid"))
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
                    "https://graph.facebook.com/v%s/%s/media"
                    % (
                        broker.whatsapp_version,
                        broker.whatsapp_from_phone,
                    ),
                    headers={
                        "Authorization": "Bearer %s" % broker.token,
                        "content-type": m.content_type,
                    },
                    data=m,
                    timeout=10,
                    proxies=self._get_proxies(),
                )
                response.raise_for_status()
                response = requests.post(
                    "https://graph.facebook.com/v%s/%s/messages"
                    % (
                        broker.whatsapp_version,
                        broker.whatsapp_from_phone,
                    ),
                    headers={"Authorization": "Bearer %s" % broker.token},
                    json=self._send_payload(
                        record.broker_channel_id,
                        media_id=response.json()["id"],
                        media_type=attachment_type,
                        media_name=attachment.name,
                    ),
                    timeout=10,
                    proxies=self._get_proxies(),
                )
                response.raise_for_status()
                message = response.json()
            if record.mail_message_id.body:
                response = requests.post(
                    "https://graph.facebook.com/v%s/%s/messages"
                    % (
                        broker.whatsapp_version,
                        broker.whatsapp_from_phone,
                    ),
                    headers={"Authorization": "Bearer %s" % broker.token},
                    json=self._send_payload(
                        record.broker_channel_id, body=record.mail_message_id.body
                    ),
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
                    _("Unable to send the whatsapp message")
                ) from exc
            else:
                _logger.warning(
                    "Issue sending message with id {}: {}".format(record.id, exc)
                )
                record.sudo().write(
                    {"notification_status": "exception", "failure_reason": exc}
                )
        if message:
            record.sudo().write(
                {
                    "notification_status": "sent",
                    "failure_reason": False,
                    "broker_message_id": message["messages"][0]["id"],
                }
            )
        if auto_commit is True:
            # pylint: disable=invalid-commit
            self.env.cr.commit()

    def _send_payload(
        self, channel, body=False, media_id=False, media_type=False, media_name=False
    ):
        if body:
            return {
                "messaging_product": "whatsapp",
                "recipient_type": "individual",
                "to": channel.token,
                "type": "text",
                "text": {"preview_url": False, "body": html2plaintext(body)},
            }
        if media_id:
            media_data = {"id": media_id}
            if media_type == "document":
                media_data["filename"] = media_name
            return {
                "messaging_product": "whatsapp",
                "recipient_type": "individual",
                "to": channel.token,
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

    def _get_author(self, broker, update):
        author_id = update.get("messages")[0].get("from")
        if author_id:
            broker_partner = self.env["res.partner.broker.channel"].search(
                [("broker_id", "=", broker.id), ("broker_token", "=", str(author_id))]
            )
            if broker_partner:
                return broker_partner.partner_id
            partner = self.env["res.partner"].search(
                [("phone_sanitized", "=", "+" + str(author_id))]
            )
            if partner:
                self.env["res.partner.broker.channel"].create(
                    {
                        "name": broker.name,
                        "partner_id": partner.id,
                        "broker_id": broker.id,
                        "broker_token": str(author_id),
                    }
                )
                return partner
            guest = self.env["mail.guest"].search(
                [("broker_id", "=", broker.id), ("broker_token", "=", str(author_id))]
            )
            if guest:
                return guest
            author_vals = self._get_author_vals(broker, author_id, update)
            if author_vals:
                return self.env["mail.guest"].create(author_vals)

        return False

    def _get_author_vals(self, broker, author_id, update):
        for contact in update.get("contacts", []):
            if contact["wa_id"] == author_id:
                return {
                    "name": contact.get("profile", {}).get("name", "Anonymous"),
                    "broker_id": broker.id,
                    "broker_token": str(author_id),
                }

    def _get_proxies(self):
        # This hook has been created in order to add a proxy if needed.
        # By default, it does nothing.
        return {}
