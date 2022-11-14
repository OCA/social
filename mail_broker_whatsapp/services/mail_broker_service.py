# Copyright 2018 ACSONE SA/NV
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).
import base64
import hashlib
import hmac
import logging
import mimetypes
import traceback
from datetime import datetime
from io import StringIO

import requests
import requests_toolbelt

from odoo import _
from odoo.exceptions import UserError
from odoo.http import request
from odoo.tools import html2plaintext

from odoo.addons.base.models.ir_mail_server import MailDeliveryException
from odoo.addons.base_rest import restapi
from odoo.addons.component.core import Component
from odoo.addons.mail_broker.services.mail_broker_service import BrokerMethodParams

_logger = logging.getLogger(__name__)


class MailBrokerWhatsappService(Component):
    _inherit = "mail.broker.base.service"
    _name = "mail.broker.whastapp.service"
    _usage = "whatsapp"
    _description = "Whatsapp Broker services"

    @restapi.method(
        [(["/<string:bot_key>/update"], "GET")],
        input_param=BrokerMethodParams(),
        auth="none",
    )
    def get_update(self, token, **kwargs):
        """Verification of the service from an external service"""
        bot_data = self.env["mail.broker"]._get_broker(
            token, state="pending", broker_type=self._usage, **kwargs
        )
        if not bot_data:
            return None
        self.collection.env = self.env(user=bot_data["webhook_user_id"])
        broker = self.env["mail.broker"].browse(bot_data["id"])
        if kwargs.get("hub").get("verify_token") != broker.whatsapp_security_key:
            return None
        broker.sudo().integrated_webhook_state = "integrated"
        response = request.make_response(kwargs.get("hub").get("challenge"))
        response.status_code = 200
        return response

    def _set_webhook(self):
        self.collection.integrated_webhook_state = "pending"

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
            return
        return self._process_update(chat, update)

    def _get_channel_vals(self, broker, token, update):
        result = super()._get_channel_vals(broker, token, update)
        for contact in update.get("contacts"):
            if contact["wa_id"] == token:
                result["name"] = contact["profile"]["name"]
                continue
        return result

    def _process_update(self, chat, updates):
        chat.ensure_one()
        body = ""
        attachments = []
        for entry in updates["entry"]:
            for change in entry["changes"]:
                if change["field"] != "messages":
                    continue
                for message in change["value"]["messages"]:
                    if message.get("text"):
                        body = message.get("text").get("body")
                    for key in ["image", "audio", "video"]:
                        if message.get(key):
                            image_id = message.get(key).get("id")
                            if image_id:
                                image_info_request = requests.get(
                                    "https://graph.facebook.com/v%s/%s" % (
                                        self.collection.whatsapp_version,
                                        image_id,
                                    ),
                                    headers={
                                        "Authorization": "Bearer %s"
                                        % self.broker_id.token,
                                    },
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
                                    "Authorization": "Bearer %s" % self.broker_id.token,
                                },
                            )
                            image_request.raise_for_status()
                            attachments.append(
                                (
                                    "{}{}".format(
                                        image_id,
                                        mimetypes.guess_extension(
                                            image_info["mime_type"]
                                        ),
                                    ),
                                    base64.b64encode(image_request.content).decode(
                                        "utf-8"
                                    ),
                                    image_info["mime_type"],
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
                        chat.message_post_broker(
                            body=body,
                            broker_type=self._usage,
                            date=datetime.fromtimestamp(int(message["timestamp"])),
                            message_id=message.get("id"),
                            subtype="mt_comment",
                            attachments=attachments,
                        )

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

    def _send(self, record, auto_commit=False, raise_exception=False, parse_mode=False):
        message = False
        try:
            if record.body:
                response = requests.post(
                    "https://graph.facebook.com/v%s/%s/messages"
                    % (
                        self.collection.whatsapp_version,
                        self.collection.whatsapp_from_phone,
                    ),
                    headers={"Authorization": "Bearer %s" % self.collection.token},
                    json=self._send_payload(record.channel_id, body=record.body),
                )
                response.raise_for_status()
                message = response.json()
            attachment_mimetype_map = self._get_whatsapp_mimetype_kind()
            for attachment in record.attachment_ids:
                if attachment.mimetype not in attachment_mimetype_map:
                    raise UserError(_("Mimetype is not valid"))
                attachment_type = attachment_mimetype_map[attachment.mimetype]
                m = requests_toolbelt.multipart.encoder.MultipartEncoder(
                    fields={
                        "file": (
                            attachment.name,
                            base64.b64decode(attachment.datas),
                            attachment.mimetype,
                        ),
                        "messaging_product": "whatsapp",
                        # "type": attachment_type
                    },
                )

                response = requests.post(
                    "https://graph.facebook.com/v%s/%s/media"
                    % (
                        self.collection.whatsapp_version,
                        self.collection.whatsapp_from_phone,
                    ),
                    headers={
                        "Authorization": "Bearer %s" % self.collection.token,
                        "content-type": m.content_type,
                    },
                    data=m,
                )
                response.raise_for_status()
                response = requests.post(
                    "https://graph.facebook.com/v%s/%s/messages"
                    % (
                        self.collection.whatsapp_version,
                        self.collection.whatsapp_from_phone,
                    ),
                    headers={"Authorization": "Bearer %s" % self.collection.token},
                    json=self._send_payload(
                        record.channel_id,
                        media_id=response.json()["id"],
                        media_type=attachment_type,
                        media_name=attachment.name,
                    ),
                )
                response.raise_for_status()
                message = response.json()
        except Exception as exc:
            buff = StringIO()
            traceback.print_exc(file=buff)
            _logger.error(buff.getvalue())
            if raise_exception:
                raise MailDeliveryException(
                    _("Unable to send the whatsapp message"), exc
                )
            else:
                _logger.warning(
                    "Issue sending message with id {}: {}".format(record.id, exc)
                )
                record.write({"state": "exception", "failure_reason": exc})
        if message:
            record.write(
                {
                    "state": "sent",
                    "message_id": message["messages"][0]["id"],
                    "failure_reason": False,
                }
            )
        if auto_commit is True:
            # pylint: disable=invalid-commit
            self.env.cr.commit()
