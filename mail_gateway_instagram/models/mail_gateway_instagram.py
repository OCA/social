# Copyright 2026 Cetmix OÜ
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import hashlib
import hmac
import logging
import mimetypes
import re
import traceback
from datetime import datetime, timezone
from io import StringIO
from urllib.parse import quote

import requests
from lxml import html as lxml_html
from markupsafe import Markup

from odoo import models
from odoo.exceptions import UserError
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
INSTAGRAM_OUTBOUND_IMAGE_MAX_BYTES = 8 * 1024 * 1024
INSTAGRAM_OUTBOUND_MEDIA_MAX_BYTES = 25 * 1024 * 1024
INSTAGRAM_OUTBOUND_TEXT_MAX_BYTES = 1000
INSTAGRAM_ECHO_MID_SEARCH_LIMIT = 100
INSTAGRAM_OUTBOUND_SUFFIX_MAP = {
    "png": ("image", "image/png", INSTAGRAM_OUTBOUND_IMAGE_MAX_BYTES),
    "jpeg": ("image", "image/jpeg", INSTAGRAM_OUTBOUND_IMAGE_MAX_BYTES),
    "jpg": ("image", "image/jpeg", INSTAGRAM_OUTBOUND_IMAGE_MAX_BYTES),
    "aac": ("audio", "audio/aac", INSTAGRAM_OUTBOUND_MEDIA_MAX_BYTES),
    "m4a": ("audio", "audio/mp4", INSTAGRAM_OUTBOUND_MEDIA_MAX_BYTES),
    "wav": ("audio", "audio/wav", INSTAGRAM_OUTBOUND_MEDIA_MAX_BYTES),
    "mp4": ("video", "video/mp4", INSTAGRAM_OUTBOUND_MEDIA_MAX_BYTES),
    "ogg": ("video", "video/ogg", INSTAGRAM_OUTBOUND_MEDIA_MAX_BYTES),
    "ogv": ("video", "video/ogg", INSTAGRAM_OUTBOUND_MEDIA_MAX_BYTES),
    "avi": ("video", "video/x-msvideo", INSTAGRAM_OUTBOUND_MEDIA_MAX_BYTES),
    "mov": ("video", "video/quicktime", INSTAGRAM_OUTBOUND_MEDIA_MAX_BYTES),
    "webm": ("video", "video/webm", INSTAGRAM_OUTBOUND_MEDIA_MAX_BYTES),
    "pdf": ("file", "application/pdf", INSTAGRAM_OUTBOUND_MEDIA_MAX_BYTES),
}
INSTAGRAM_OUTBOUND_MIMETYPE_MAP = {
    "image/png": ("image", "image/png", INSTAGRAM_OUTBOUND_IMAGE_MAX_BYTES),
    "image/jpeg": ("image", "image/jpeg", INSTAGRAM_OUTBOUND_IMAGE_MAX_BYTES),
    "audio/aac": ("audio", "audio/aac", INSTAGRAM_OUTBOUND_MEDIA_MAX_BYTES),
    "audio/x-aac": ("audio", "audio/aac", INSTAGRAM_OUTBOUND_MEDIA_MAX_BYTES),
    "audio/mp4": ("audio", "audio/mp4", INSTAGRAM_OUTBOUND_MEDIA_MAX_BYTES),
    "audio/mp4a-latm": ("audio", "audio/mp4", INSTAGRAM_OUTBOUND_MEDIA_MAX_BYTES),
    "audio/x-m4a": ("audio", "audio/mp4", INSTAGRAM_OUTBOUND_MEDIA_MAX_BYTES),
    "audio/wav": ("audio", "audio/wav", INSTAGRAM_OUTBOUND_MEDIA_MAX_BYTES),
    "audio/x-wav": ("audio", "audio/wav", INSTAGRAM_OUTBOUND_MEDIA_MAX_BYTES),
    "audio/vnd.wave": ("audio", "audio/wav", INSTAGRAM_OUTBOUND_MEDIA_MAX_BYTES),
    "audio/wave": ("audio", "audio/wav", INSTAGRAM_OUTBOUND_MEDIA_MAX_BYTES),
    "video/mp4": ("video", "video/mp4", INSTAGRAM_OUTBOUND_MEDIA_MAX_BYTES),
    "video/ogg": ("video", "video/ogg", INSTAGRAM_OUTBOUND_MEDIA_MAX_BYTES),
    "audio/ogg": ("video", "video/ogg", INSTAGRAM_OUTBOUND_MEDIA_MAX_BYTES),
    "video/x-msvideo": ("video", "video/x-msvideo", INSTAGRAM_OUTBOUND_MEDIA_MAX_BYTES),
    "video/quicktime": ("video", "video/quicktime", INSTAGRAM_OUTBOUND_MEDIA_MAX_BYTES),
    "video/webm": ("video", "video/webm", INSTAGRAM_OUTBOUND_MEDIA_MAX_BYTES),
    "application/pdf": ("file", "application/pdf", INSTAGRAM_OUTBOUND_MEDIA_MAX_BYTES),
}


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
        if not message or message.get("is_deleted"):
            return
        is_echo = bool(message.get("is_echo"))
        if is_echo and not gateway.instagram_show_own_messages:
            return
        if is_echo:
            igsid = (item.get("recipient") or {}).get("id")
        else:
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
        if (update.get("message") or {}).get("is_echo"):
            author_id = (update.get("recipient") or {}).get("id")
        else:
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
        is_echo = bool(message.get("is_echo"))
        if is_echo and self._instagram_echo_already_sent(chat, message.get("mid")):
            return
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
        if not is_echo and author and author._name == "mail.guest":
            chat = chat.with_user(self.env.ref("base.public_user").id).with_context(
                guest=author
            )
        post_kwargs = {
            "body": body,
            "author_id": (
                self.env.user.partner_id.id
                if is_echo
                else (author and author._name == "res.partner" and author.id)
            ),
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

    def _instagram_echo_already_sent(self, chat, mid):
        """Return whether this Graph mid was already sent from Odoo on chat.

        Searches the 100 newest gateway notifications on the channel
        (mail.notification has no create_date). fields.Json cannot be
        searched, so membership is checked in Python.

        :param chat: gateway discuss.channel
        :type chat: discuss.channel
        :param mid: Instagram webhook message id
        :type mid: str | None
        :return: True when the echo should be skipped
        :rtype: bool
        """
        if not mid:
            return False
        notifications = self.env["mail.notification"].search(
            [
                ("gateway_channel_id", "=", chat.id),
                ("notification_type", "=", "gateway"),
            ],
            order="id desc",
            limit=INSTAGRAM_ECHO_MID_SEARCH_LIMIT,
        )
        for notification in notifications:
            if notification.gateway_message_id == mid:
                return True
            if mid in (notification.instagram_sent_mids or []):
                return True
        return False

    def _instagram_plaintext_from_html(self, body):
        """Convert Discuss HTML to Instagram plaintext without footnotes.

        Rewrites each ``<a href>`` so a URL-only link is sent once and a
        labelled link becomes ``{text} ({href})``, then runs
        ``html2plaintext(..., include_references=False)``. Empty or
        whitespace-only bodies skip the parser.

        :param body: HTML body from the mail message
        :type body: str | bool | None
        :return: plaintext to send, or an empty string
        :rtype: str
        """
        html_body = body or ""
        if not str(html_body).strip():
            return ""
        tree = lxml_html.fromstring(str(html_body))
        for link in tree.xpath("descendant-or-self::a[@href]"):
            href = link.get("href") or ""
            text = "".join(link.itertext()).strip()
            replacement = href if text == href else f"{text} ({href})"
            for child in list(link):
                link.remove(child)
            link.tag = "span"
            for key in list(link.attrib):
                del link.attrib[key]
            link.text = replacement
        rewritten = lxml_html.tostring(tree, encoding="unicode")
        return html2plaintext(rewritten, include_references=False)

    def _instagram_classify_outbound_attachment(self, attachment):
        """Return Graph type and canonical mimetype for an attachment.

        Classification uses the filename's last suffix against Meta's
        Send Messages formats. When that suffix is not recognised, the
        stored mimetype is matched against a host-independent alias list.

        :param attachment: attachment to send
        :type attachment: ir.attachment
        :return: ``(graph_type, canonical_mimetype)``
        :rtype: tuple
        """
        if attachment.type != "binary":
            raise UserError(
                self.env._(
                    "Instagram cannot send URL attachments. Upload the file "
                    "instead (%(name)s).",
                    name=attachment.name,
                )
            )
        name = attachment.name or ""
        suffix = name.rsplit(".", 1)[-1].lower() if "." in name else ""
        classified = INSTAGRAM_OUTBOUND_SUFFIX_MAP.get(suffix)
        if not classified:
            classified = INSTAGRAM_OUTBOUND_MIMETYPE_MAP.get(
                (attachment.mimetype or "").lower()
            )
        if not classified:
            raise UserError(
                self.env._(
                    "Instagram does not accept this attachment type: %(name)s.",
                    name=attachment.name,
                )
            )
        graph_type, canonical_mimetype, max_bytes = classified
        if (attachment.file_size or 0) > max_bytes:
            raise UserError(
                self.env._(
                    "Attachment %(name)s exceeds the Instagram size limit "
                    "(%(limit)s bytes).",
                    name=attachment.name,
                    limit=max_bytes,
                )
            )
        return graph_type, canonical_mimetype

    def _instagram_prepare_outbound(self, attachments, text):
        """Validate outbound payload and return classified attachments.

        Runs before the first Graph POST so an invalid file or over-long
        text cannot send earlier attachments.

        :param attachments: attachments in send order
        :type attachments: ir.attachment
        :param text: plaintext after the HTML link rewrite
        :type text: str
        :return: list of ``(attachment, graph_type, canonical_mimetype)``
        :rtype: list
        """
        prepared = []
        for attachment in attachments:
            graph_type, canonical_mimetype = (
                self._instagram_classify_outbound_attachment(attachment)
            )
            prepared.append((attachment, graph_type, canonical_mimetype))
        if text and len(text.encode("utf-8")) > INSTAGRAM_OUTBOUND_TEXT_MAX_BYTES:
            raise UserError(
                self.env._(
                    "Instagram text messages cannot exceed %(limit)s bytes.",
                    limit=INSTAGRAM_OUTBOUND_TEXT_MAX_BYTES,
                )
            )
        return prepared

    def _instagram_attachment_public_url(self, attachment, base_url):
        """Build a tokenized media URL Meta can fetch.

        ``generate_access_token`` writes a permanent token in the current
        transaction. The caller must commit when a token was just created
        so Meta's fetch (another HTTP worker) can validate it. The token
        is a path segment, not a query parameter: Graph 2018007 is Meta
        failing to download ``payload.url``, and query strings on
        ``/web/content`` are not fetched reliably. The filename is
        quoted with ``safe=""`` so ``/`` cannot break Werkzeug's
        ``<string:filename>`` route. Canonical ``Content-Type`` is set
        by the media controller from the D12 map.

        :param attachment: binary attachment
        :type attachment: ir.attachment
        :param base_url: already-read ``web.base.url`` without a trailing slash
        :type base_url: str
        :return: absolute URL with token and filename in the path
        :rtype: str
        """
        tokens = attachment.sudo().generate_access_token()
        token = quote(str(tokens[0] if tokens else ""), safe="")
        filename = quote(attachment.name or "", safe="")
        return (
            f"{base_url}/mail_gateway_instagram/content/"
            f"{attachment.id}/{token}/{filename}"
        )

    def _instagram_commit_new_access_tokens(self):
        """Commit newly written tokens so Meta's fetch can validate them.

        Discuss ``_send`` runs inside ``message_post`` with
        ``auto_commit=False``. Internal uploads store no token until
        ``generate_access_token`` writes it in this transaction
        (``mail/controllers/attachment.py``). Graph's fetcher is another
        HTTP worker and cannot see an uncommitted token, which Meta
        reports as 2018007. Tests patch ``Cursor.commit`` to raise, so
        skip when ``registry.in_test_mode()``.
        """
        if self.env.registry.in_test_mode():
            return
        # pylint: disable=invalid-commit
        self.env.cr.commit()

    def _instagram_attachment_message(self, graph_type, url):
        """Return the Graph ``message`` object for one outbound attachment.

        Images use ``attachments`` as a one-item list. Graph validates
        ``message[attachments][0]`` as an object with string keys
        (IGApiException code 100 if a bare object is sent). Audio, video
        and file use singular ``attachment``.

        :param graph_type: ``image``, ``audio``, ``video`` or ``file``
        :type graph_type: str
        :param url: public URL Meta should fetch
        :type url: str
        :return: message payload fragment
        :rtype: dict
        """
        payload = {"type": graph_type, "payload": {"url": url}}
        if graph_type == "image":
            return {"attachments": [payload]}
        return {"attachment": payload}

    def _instagram_graph_http_error_message(self, response):
        """Return a Graph HTTP error string without attachment tokens.

        Meta may echo ``payload.url`` (including ``access_token``) in the
        JSON body. That must not land in logs or ``failure_reason``.

        :param response: Graph HTTP response
        :type response: requests.Response
        :return: operator-visible error text
        :rtype: str
        """
        raw = response.text or ""
        redacted = re.sub(r"access_token=[^&\s\"']+", "access_token=REDACTED", raw)
        redacted = re.sub(
            r"(/mail_gateway_instagram/content/\d+/)[^/\"'\s]+",
            r"\1REDACTED",
            redacted,
        )
        return (
            f"{response.status_code} {response.reason} for url: "
            f"{response.url} {redacted}"
        )

    def _instagram_post_graph_message(self, gateway, payload):
        """POST one Send Messages payload to graph.instagram.com.

        :param gateway: Instagram mail.gateway
        :type gateway: mail.gateway
        :param payload: JSON body
        :type payload: dict
        :return: parsed JSON response
        :rtype: dict
        """
        response = requests.post(
            f"https://graph.instagram.com/"
            f"v{gateway.instagram_version}/"
            f"{gateway.instagram_account_id}/messages",
            headers={"Authorization": f"Bearer {gateway.token}"},
            json=payload,
            timeout=INSTAGRAM_REQUEST_TIMEOUT,
            proxies=self._get_proxies(),
        )
        if not response.ok:
            raise requests.HTTPError(
                self._instagram_graph_http_error_message(response),
                response=response,
            )
        return response.json()

    def _send(
        self,
        gateway,
        record,
        auto_commit=False,
        raise_exception=False,
        parse_mode=False,
    ):
        message = False
        sent_mids = []
        try:
            attachments = record.mail_message_id.attachment_ids.sorted("id")
            text = self._instagram_plaintext_from_html(self._get_message_body(record))
            if attachments or text:
                prepared = self._instagram_prepare_outbound(attachments, text)
                recipient_id = record.gateway_channel_id.gateway_channel_token
                if prepared:
                    base_url = (
                        self.env["ir.config_parameter"].sudo().get_param("web.base.url")
                        or ""
                    ).rstrip("/")
                    media = []
                    wrote_access_token = False
                    for attachment, graph_type, _canonical_mimetype in prepared:
                        if not attachment.sudo().access_token:
                            wrote_access_token = True
                        url = self._instagram_attachment_public_url(
                            attachment, base_url
                        )
                        media.append((graph_type, url))
                    if wrote_access_token:
                        self._instagram_commit_new_access_tokens()
                    for graph_type, url in media:
                        message = self._instagram_post_graph_message(
                            gateway,
                            {
                                "recipient": {"id": recipient_id},
                                "message": self._instagram_attachment_message(
                                    graph_type, url
                                ),
                            },
                        )
                        if message.get("message_id"):
                            sent_mids.append(message["message_id"])
                if text:
                    message = self._instagram_post_graph_message(
                        gateway,
                        {
                            "recipient": {"id": recipient_id},
                            "message": {"text": text},
                        },
                    )
                    if message.get("message_id"):
                        sent_mids.append(message["message_id"])
        except Exception as exc:
            buff = StringIO()
            traceback.print_exc(file=buff)
            _logger.error(buff.getvalue())
            if raise_exception:
                raise MailDeliveryException(
                    self.env._("Unable to send the Instagram message")
                ) from exc
            _logger.warning("Issue sending message with id %s: %s", record.id, exc)
            vals = {
                "notification_status": "exception",
                "failure_reason": exc,
                "failure_type": "unknown",
            }
            if sent_mids:
                vals["instagram_sent_mids"] = sent_mids
                vals["gateway_message_id"] = sent_mids[-1]
            record.sudo().write(vals)
        else:
            if message:
                record.sudo().write(
                    {
                        "notification_status": "sent",
                        "failure_reason": False,
                        "failure_type": False,
                        "gateway_message_id": message.get("message_id"),
                        "instagram_sent_mids": sent_mids,
                    }
                )
        if auto_commit is True:
            # pylint: disable=invalid-commit
            self.env.cr.commit()

    def _get_proxies(self):
        # Extension point for deployments that need an outbound HTTP proxy.
        return {}
