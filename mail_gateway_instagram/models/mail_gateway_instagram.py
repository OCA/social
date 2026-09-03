# Copyright 2026 Cetmix OÜ
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import hashlib
import hmac
import logging
import mimetypes
import traceback
from datetime import datetime, timezone
from io import StringIO

import requests
from markupsafe import Markup

from odoo import models
from odoo.http import request
from odoo.tools import html2plaintext, html_escape

from odoo.addons.base.models.ir_mail_server import MailDeliveryException

_logger = logging.getLogger(__name__)

# Meta documents inbound Instagram media maxima as 8MB (image) / 25MB (audio,
# video, file). Cap downloads at the larger figure.
INSTAGRAM_ATTACHMENT_MAX_BYTES = 25 * 1024 * 1024
INSTAGRAM_REQUEST_TIMEOUT = 10
INSTAGRAM_DOWNLOAD_TYPES = frozenset({"image", "video", "audio", "file"})
INSTAGRAM_LINK_TYPES = frozenset(
    {
        "share",
        "story_mention",
        "ig_reel",
        "reel",
        "ig_post",
        "story",
        "ig_story",
    }
)


class MailGatewayInstagramService(models.AbstractModel):
    _inherit = "mail.gateway.abstract"
    _name = "mail.gateway.instagram"
    _description = "Instagram Gateway services"

    def _set_webhook(self, gateway):
        gateway.integrated_webhook_state = "pending"

    def _receive_get_update(self, bot_data, req, **kwargs):
        gateway = self.env["mail.gateway"].browse(bot_data["id"])
        if kwargs.get("hub.mode") != "subscribe":
            return None
        if kwargs.get("hub.verify_token") != gateway.instagram_security_key:
            return None
        if gateway.integrated_webhook_state != "pending":
            return None
        gateway.sudo().integrated_webhook_state = "integrated"
        response = request.make_response(kwargs.get("hub.challenge"))
        response.status_code = 200
        return response

    def _verify_update(self, bot_data, kwargs):
        signature = request.httprequest.headers.get("x-hub-signature-256")
        secret = bot_data.get("webhook_secret")
        if not signature or not secret:
            return False
        hex_dig = hmac.new(
            secret.encode(),
            request.httprequest.data,
            hashlib.sha256,
        ).hexdigest()
        return hmac.compare_digest(f"sha256={hex_dig}", signature)

    def _receive_update(self, gateway, update):
        payloads = update if isinstance(update, list) else [update]
        for payload in payloads:
            if not isinstance(payload, dict):
                continue
            for entry in payload.get("entry") or []:
                if not isinstance(entry, dict):
                    continue
                if gateway.instagram_account_id and str(entry.get("id") or "") != str(
                    gateway.instagram_account_id
                ):
                    continue
                for item in entry.get("messaging") or []:
                    self._receive_messaging_item(gateway, item)

    def _receive_messaging_item(self, gateway, item):
        message = item.get("message")
        if not message or message.get("is_echo") or message.get("is_deleted"):
            return
        igsid = (item.get("sender") or {}).get("id")
        if not igsid:
            return
        chat = self._get_channel(gateway, igsid, item, force_create=True)
        if not chat:
            return
        self._process_update(chat, item)

    def _get_channel_vals(self, gateway, token, update):
        result = super()._get_channel_vals(gateway, token, update)
        author = self._get_author(gateway, update)
        result["name"] = author.name if author else str(token)
        return result

    def _get_author(self, gateway, update):
        author_id = (update.get("sender") or {}).get("id")
        if not author_id:
            return False
        author_token = str(author_id)
        gateway_partner = self.env["res.partner.gateway.channel"].search(
            [
                ("gateway_id", "=", gateway.id),
                ("gateway_token", "=", author_token),
            ]
        )
        if gateway_partner:
            return gateway_partner.partner_id
        guest = self.env["mail.guest"].search(
            [
                ("gateway_id", "=", gateway.id),
                ("gateway_token", "=", author_token),
            ]
        )
        if guest:
            return guest
        return self.env["mail.guest"].create(self._get_author_vals(gateway, author_id))

    def _get_author_vals(self, gateway, author_id):
        return {
            "name": self._get_instagram_profile_name(gateway, author_id),
            "gateway_id": gateway.id,
            "gateway_token": str(author_id),
        }

    def _process_update(self, chat, item):
        chat.ensure_one()
        message = item.get("message") or {}
        body = html_escape(message.get("text") or "")
        attachments = []
        for index, attachment in enumerate(message.get("attachments") or []):
            attachment_type = attachment.get("type")
            url = (attachment.get("payload") or {}).get("url")
            if not url:
                continue
            if attachment_type in INSTAGRAM_LINK_TYPES:
                if body:
                    body += Markup(" ")
                body += Markup('<a target="_blank" href="%s">%s</a>') % (
                    url,
                    attachment_type,
                )
                continue
            if attachment_type not in INSTAGRAM_DOWNLOAD_TYPES:
                continue
            content, content_type = self._download_instagram_attachment(
                chat.gateway_id, url
            )
            if not content:
                continue
            extension = mimetypes.guess_extension(content_type or "") or ""
            attachments.append(
                (f"{attachment_type}-{index}{extension}", content, {}),
            )
        if not body and not attachments:
            return
        author = self._get_author(chat.gateway_id, item)
        if author and author._name == "mail.guest":
            chat = chat.with_user(self.env.ref("base.public_user").id).with_context(
                guest=author
            )
        post_kwargs = {
            "body": body,
            "author_id": author and author._name == "res.partner" and author.id,
            "gateway_type": "instagram",
            "subtype_xmlid": "mail.mt_comment",
            "message_type": "comment",
            "attachments": attachments,
        }
        message_date = self._instagram_timestamp_to_datetime(item.get("timestamp"))
        if message_date:
            post_kwargs["date"] = message_date
        new_message = chat.sudo().message_post(**post_kwargs)
        self._post_process_message(new_message, chat)

    def _instagram_timestamp_to_datetime(self, timestamp):
        """Convert an Instagram webhook timestamp to a naive UTC datetime.

        Instagram Messaging (Messenger-family) ``messaging[].timestamp``
        values are Unix epoch **milliseconds**, not seconds.

        :param timestamp: webhook timestamp (int, str, or empty)
        :type timestamp: int | str | None
        :return: naive UTC datetime, or False when the value is missing
            or not numeric
        :rtype: datetime | bool
        """
        if timestamp in (None, False, ""):
            return False
        try:
            timestamp_ms = int(timestamp)
        except (TypeError, ValueError):
            _logger.debug("Instagram webhook timestamp %r is not numeric", timestamp)
            return False
        return datetime.fromtimestamp(timestamp_ms / 1000.0, tz=timezone.utc).replace(
            tzinfo=None, microsecond=0
        )

    def _get_instagram_profile_name(self, gateway, igsid):
        """Best-effort display name for an IGSID. Never raises.

        :param gateway: Instagram mail.gateway record
        :type gateway: mail.gateway
        :param igsid: Instagram-scoped sender id
        :type igsid: str
        :return: profile name, username, or the IGSID string
        :rtype: str
        """
        fallback = str(igsid)
        try:
            response = requests.get(
                f"https://graph.instagram.com/v{gateway.instagram_version}/{igsid}",
                params={"fields": "name,username"},
                headers={"Authorization": f"Bearer {gateway.token}"},
                timeout=INSTAGRAM_REQUEST_TIMEOUT,
                proxies=self._get_proxies(),
            )
            response.raise_for_status()
            data = response.json()
        except Exception:
            _logger.debug(
                "Instagram profile lookup failed for gateway %s",
                gateway.id,
                exc_info=True,
            )
            return fallback
        return data.get("name") or data.get("username") or fallback

    def _download_instagram_attachment(self, gateway, url):
        """Download a webhook CDN attachment, capped in size.

        Instagram ``payload.url`` values are pre-signed CDN links and do
        not need the access token.

        :param gateway: Instagram mail.gateway record (used only for logs)
        :type gateway: mail.gateway
        :param url: attachment CDN URL
        :type url: str
        :return: ``(content, content_type)`` or ``(False, False)``
        :rtype: tuple
        """
        try:
            with requests.get(
                url,
                timeout=INSTAGRAM_REQUEST_TIMEOUT,
                proxies=self._get_proxies(),
                stream=True,
            ) as response:
                response.raise_for_status()
                content_length = response.headers.get("Content-Length")
                if (
                    content_length
                    and int(content_length) > INSTAGRAM_ATTACHMENT_MAX_BYTES
                ):
                    _logger.warning(
                        "Instagram attachment exceeds size cap for gateway %s",
                        gateway.id,
                    )
                    return False, False
                chunks = []
                total = 0
                for chunk in response.iter_content(65536):
                    total += len(chunk)
                    if total > INSTAGRAM_ATTACHMENT_MAX_BYTES:
                        _logger.warning(
                            "Instagram attachment exceeds size cap for gateway %s",
                            gateway.id,
                        )
                        return False, False
                    chunks.append(chunk)
                content_type = (response.headers.get("Content-Type") or "").split(";")[
                    0
                ]
                return b"".join(chunks), content_type.strip()
        except Exception:
            _logger.debug(
                "Instagram attachment download failed for gateway %s",
                gateway.id,
                exc_info=True,
            )
            return False, False

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
            body = self._get_message_body(record)
            text = html2plaintext(body)
            if text:
                response = requests.post(
                    f"https://graph.instagram.com/"
                    f"v{gateway.instagram_version}/"
                    f"{gateway.instagram_account_id}/messages",
                    headers={"Authorization": f"Bearer {gateway.token}"},
                    json={
                        "recipient": {
                            "id": record.gateway_channel_id.gateway_channel_token,
                        },
                        "message": {"text": text},
                    },
                    timeout=INSTAGRAM_REQUEST_TIMEOUT,
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
                    self.env._("Unable to send the Instagram message")
                ) from exc
            _logger.warning("Issue sending message with id %s: %s", record.id, exc)
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
                    "gateway_message_id": message.get("message_id"),
                }
            )
        if auto_commit is True:
            # pylint: disable=invalid-commit
            self.env.cr.commit()

    def _get_proxies(self):
        # Extension point for deployments that need an outbound HTTP proxy.
        return {}
