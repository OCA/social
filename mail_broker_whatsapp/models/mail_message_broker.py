# Copyright 2022 Creu Blanca
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
import base64
import logging
import traceback
from io import StringIO

import requests
import requests_toolbelt

from odoo import _, models
from odoo.exceptions import UserError
from odoo.tools import html2plaintext

from odoo.addons.base.models.ir_mail_server import MailDeliveryException

_logger = logging.getLogger(__name__)


class MailMessageBroker(models.Model):
    _inherit = "mail.message.broker"

    def _send_whatsapp_payload(
        self, body=False, media_id=False, media_type=False, media_name=False
    ):
        if body:
            return {
                "messaging_product": "whatsapp",
                "recipient_type": "individual",
                "to": self.channel_id.token,
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
                "to": self.channel_id.token,
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

    def _send_whatsapp(
        self, auto_commit=False, raise_exception=False, parse_mode=False
    ):
        message = False
        try:
            if self.body:
                response = requests.post(
                    "https://graph.facebook.com/v13.0/%s/messages"
                    % self.channel_id.broker_id.whatsapp_from_phone,
                    headers={
                        "Authorization": "Bearer %s" % self.channel_id.broker_id.token,
                    },
                    json=self._send_whatsapp_payload(body=self.body),
                )
                response.raise_for_status()
                message = response.json()
            attachment_mimetype_map = self._get_whatsapp_mimetype_kind()
            for attachment in self.attachment_ids:
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
                    "https://graph.facebook.com/v13.0/%s/media"
                    % self.channel_id.broker_id.whatsapp_from_phone,
                    headers={
                        "Authorization": "Bearer %s" % self.channel_id.broker_id.token,
                        "content-type": m.content_type,
                    },
                    data=m,
                )
                response.raise_for_status()
                response = requests.post(
                    "https://graph.facebook.com/v13.0/%s/messages"
                    % self.channel_id.broker_id.whatsapp_from_phone,
                    headers={
                        "Authorization": "Bearer %s" % self.channel_id.broker_id.token,
                    },
                    json=self._send_whatsapp_payload(
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
                    "Issue sending message with id {}: {}".format(self.id, exc)
                )
                self.write({"state": "exception", "failure_reason": exc})
        if message:
            self.write(
                {
                    "state": "sent",
                    "message_id": message["messages"][0]["id"],
                    "failure_reason": False,
                }
            )
        if auto_commit is True:
            # pylint: disable=invalid-commit
            self._cr.commit()
