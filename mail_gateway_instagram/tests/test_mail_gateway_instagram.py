# Copyright 2026 Cetmix OÜ
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import hashlib
import hmac
import json
from datetime import datetime
from unittest.mock import MagicMock, patch

import requests
from markupsafe import Markup

from odoo.tests.common import tagged
from odoo.tools import mute_logger

from odoo.addons.base.models.ir_mail_server import MailDeliveryException
from odoo.addons.mail_gateway.tests.common import MailGatewayTestCase
from odoo.addons.mail_gateway_instagram.models.mail_gateway_instagram import (
    INSTAGRAM_ATTACHMENT_MAX_BYTES,
    INSTAGRAM_OUTBOUND_IMAGE_MAX_BYTES,
)

IGSID = "12345678901234"
IGSID_OTHER = "98765432109876"
IGID = "17841400000000000"
WEBHOOK = "ig_hook"
CHALLENGE = "1158201444"


@tagged("-at_install", "post_install")
class TestMailGatewayInstagram(MailGatewayTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.gateway = cls.env["mail.gateway"].create(
            {
                "name": "Instagram",
                "gateway_type": "instagram",
                "token": "ig-access-token",
                "instagram_security_key": "verify-token",
                "instagram_account_id": IGID,
                "webhook_secret": "APP-SECRET",
                "member_ids": [(4, cls.env.user.id)],
            }
        )
        cls.text_message = cls._messaging_payload(
            {
                "sender": {"id": IGSID},
                "recipient": {"id": IGID},
                "timestamp": 1569262485349,
                "message": {"mid": "mid.1", "text": "Hello"},
            }
        )

    @classmethod
    def _messaging_payload(cls, item):
        return {
            "object": "instagram",
            "entry": [
                {
                    "id": IGID,
                    "time": 1569262486134,
                    "messaging": [item],
                }
            ],
        }

    def setUp(self):
        super().setUp()
        get_patcher = patch(
            "odoo.addons.mail_gateway_instagram.models.mail_gateway_instagram.requests.get"
        )
        self.requests_get = get_patcher.start()
        self.addCleanup(get_patcher.stop)
        self.requests_get.side_effect = self._mock_profile_get

    def _mock_profile_get(self, url, **kwargs):
        response = MagicMock()
        response.__enter__.return_value = response
        response.__exit__.return_value = None
        response.raise_for_status.return_value = None
        response.json.return_value = {"name": "Jane Doe", "username": "jane_doe"}
        response.headers = {}
        response.iter_content.return_value = iter(())
        return response

    def _mock_image_get(self, url, **kwargs):
        if "lookaside.fbsbx.com" in url:
            response = MagicMock()
            response.__enter__.return_value = response
            response.__exit__.return_value = None
            response.raise_for_status.return_value = None
            response.headers = {
                "Content-Type": "image/jpeg",
                "Content-Length": "4",
            }
            response.iter_content.return_value = iter([b"JPEG"])
            return response
        return self._mock_profile_get(url, **kwargs)

    def _mock_video_get(self, url, **kwargs):
        if "lookaside.fbsbx.com" in url:
            response = MagicMock()
            response.__enter__.return_value = response
            response.__exit__.return_value = None
            response.raise_for_status.return_value = None
            response.headers = {
                "Content-Type": "video/mp4",
                "Content-Length": "4",
            }
            response.iter_content.return_value = iter([b"MP4V"])
            return response
        return self._mock_profile_get(url, **kwargs)

    def _mock_oversized_attachment_get(self, url, **kwargs):
        if "lookaside.fbsbx.com" in url:
            response = MagicMock()
            response.__enter__.return_value = response
            response.__exit__.return_value = None
            response.raise_for_status.return_value = None
            response.headers = {
                "Content-Type": "image/jpeg",
                "Content-Length": str(INSTAGRAM_ATTACHMENT_MAX_BYTES + 1),
            }
            response.iter_content.return_value = iter([b"JPEG"])
            return response
        return self._mock_profile_get(url, **kwargs)

    def integrate_webhook(self):
        self.gateway.webhook_key = WEBHOOK
        self.gateway.set_webhook()
        return self.url_open(
            f"/gateway/{self.gateway.gateway_type}/{WEBHOOK}/update?hub.mode=subscribe"
            f"&hub.verify_token={self.gateway.instagram_security_key}&hub.challenge={CHALLENGE}",
        )

    def set_message(self, message, webhook, headers=True, signature_body=None):
        data = json.dumps(message)
        headers_dict = {"Content-Type": "application/json"}
        if headers:
            hex_dig = hmac.new(
                self.gateway.webhook_secret.encode(),
                (signature_body if signature_body is not None else data).encode(),
                hashlib.sha256,
            ).hexdigest()
            headers_dict["x-hub-signature-256"] = f"sha256={hex_dig}"
        return self.url_open(
            f"/gateway/{self.gateway.gateway_type}/{webhook}/update",
            data=data,
            headers=headers_dict,
        )

    def receive_message(self, message):
        self.integrate_webhook()
        self.set_message(message, WEBHOOK)
        return self.env["discuss.channel"].search(
            [("gateway_id", "=", self.gateway.id)]
        )

    def test_gateway_type_selection(self):
        self.assertIn(
            "instagram",
            dict(self.env["mail.gateway"]._fields["gateway_type"].selection),
        )
        message_selection = (
            self.env["mail.message"]
            ._fields["gateway_type"]
            ._description_selection(self.env)
        )
        self.assertIn("instagram", dict(message_selection))

    def test_receive_get_update_ok(self):
        response = self.integrate_webhook()
        self.assertEqual(self.gateway.integrated_webhook_state, "integrated")
        self.assertEqual(response.text, CHALLENGE)

    def test_receive_get_update_wrong_token(self):
        self.gateway.webhook_key = WEBHOOK
        self.gateway.set_webhook()
        self.url_open(
            "/gateway/{}/{}/update?hub.mode=subscribe"
            "&hub.verify_token={}&hub.challenge={}".format(
                self.gateway.gateway_type,
                WEBHOOK,
                self.gateway.instagram_security_key + "x",
                CHALLENGE,
            ),
        )
        self.assertEqual(self.gateway.integrated_webhook_state, "pending")

    def test_receive_get_update_not_pending(self):
        result = self.env["mail.gateway.instagram"]._receive_get_update(
            self.gateway._get_gateway_data(),
            None,
            **{
                "hub.mode": "subscribe",
                "hub.verify_token": self.gateway.instagram_security_key,
                "hub.challenge": CHALLENGE,
            },
        )
        self.assertIsNone(result)
        self.assertFalse(self.gateway.integrated_webhook_state)

    def test_instagram_timestamp_to_datetime(self):
        service = self.env["mail.gateway.instagram"]
        self.assertEqual(
            service._instagram_timestamp_to_datetime(1569262485349),
            datetime(2019, 9, 23, 18, 14, 45),
        )
        self.assertEqual(
            service._instagram_timestamp_to_datetime("1569262485349"),
            datetime(2019, 9, 23, 18, 14, 45),
        )
        self.assertFalse(service._instagram_timestamp_to_datetime(False))
        self.assertFalse(service._instagram_timestamp_to_datetime("not-a-time"))

    def test_receive_text_creates_channel(self):
        chat = self.receive_message(self.text_message)
        self.assertEqual(len(chat), 1)
        self.assertEqual(chat.gateway_channel_token, IGSID)
        self.assertEqual(chat.name, "Jane Doe")
        messages = chat.message_ids.filtered(lambda m: m.message_type == "comment")
        self.assertEqual(len(messages), 1)
        self.assertIn("Hello", messages.body)
        self.assertFalse(messages.author_id)
        guest = self.env["mail.guest"].search(
            [
                ("gateway_id", "=", self.gateway.id),
                ("gateway_token", "=", IGSID),
            ]
        )
        self.assertEqual(len(guest), 1)
        self.assertFalse(
            self.env["res.partner.gateway.channel"].search(
                [
                    ("gateway_id", "=", self.gateway.id),
                    ("gateway_token", "=", IGSID),
                ]
            )
        )

    def test_second_dm_reuses_channel(self):
        chat = self.receive_message(self.text_message)
        guest = self.env["mail.guest"].search(
            [
                ("gateway_id", "=", self.gateway.id),
                ("gateway_token", "=", IGSID),
            ]
        )
        self.set_message(
            self._messaging_payload(
                {
                    "sender": {"id": IGSID},
                    "recipient": {"id": IGID},
                    "timestamp": 1569262486000,
                    "message": {"mid": "mid.2", "text": "Again"},
                }
            ),
            WEBHOOK,
        )
        chats = self.env["discuss.channel"].search(
            [("gateway_id", "=", self.gateway.id)]
        )
        self.assertEqual(chats, chat)
        comments = chat.message_ids.filtered(lambda m: m.message_type == "comment")
        self.assertEqual(len(comments), 2)
        guests = self.env["mail.guest"].search(
            [
                ("gateway_id", "=", self.gateway.id),
                ("gateway_token", "=", IGSID),
            ]
        )
        self.assertEqual(guests, guest)

    def test_different_igsid_creates_second_channel(self):
        self.receive_message(self.text_message)
        self.set_message(
            self._messaging_payload(
                {
                    "sender": {"id": IGSID_OTHER},
                    "recipient": {"id": IGID},
                    "timestamp": 1569262486000,
                    "message": {"mid": "mid.3", "text": "Other"},
                }
            ),
            WEBHOOK,
        )
        chats = self.env["discuss.channel"].search(
            [("gateway_id", "=", self.gateway.id)]
        )
        self.assertEqual(len(chats), 2)
        self.assertEqual(
            set(chats.mapped("gateway_channel_token")), {IGSID, IGSID_OTHER}
        )

    def test_entry_for_other_account_is_skipped(self):
        payload = self._messaging_payload(
            {
                "sender": {"id": IGSID},
                "recipient": {"id": IGID},
                "timestamp": 1569262485349,
                "message": {"mid": "mid.other-ig", "text": "Hello"},
            }
        )
        payload["entry"][0]["id"] = "99999999999999999"
        self.integrate_webhook()
        self.set_message(payload, WEBHOOK)
        self.assertFalse(
            self.env["discuss.channel"].search([("gateway_id", "=", self.gateway.id)])
        )

    def test_author_partner_gateway_channel(self):
        partner = self.env["res.partner"].create({"name": "Known"})
        self.env["res.partner.gateway.channel"].create(
            {
                "partner_id": partner.id,
                "gateway_id": self.gateway.id,
                "gateway_token": IGSID,
            }
        )
        chat = self.receive_message(self.text_message)
        comments = chat.message_ids.filtered(lambda m: m.message_type == "comment")
        self.assertEqual(comments.author_id, partner)
        self.assertEqual(chat.name, "Known")
        self.assertFalse(
            self.env["mail.guest"].search(
                [
                    ("gateway_id", "=", self.gateway.id),
                    ("gateway_token", "=", IGSID),
                ]
            )
        )

    def test_author_partner_who_is_gateway_member_names_channel(self):
        partner = self.env.user.partner_id
        self.env["res.partner.gateway.channel"].create(
            {
                "partner_id": partner.id,
                "gateway_id": self.gateway.id,
                "gateway_token": IGSID,
            }
        )
        chat = self.receive_message(self.text_message)
        self.assertEqual(chat.name, partner.name)
        comments = chat.message_ids.filtered(lambda m: m.message_type == "comment")
        self.assertEqual(comments.author_id, partner)

    def test_echo_posts_nothing(self):
        self.integrate_webhook()
        self.set_message(
            self._messaging_payload(
                {
                    "sender": {"id": IGID},
                    "recipient": {"id": IGSID},
                    "timestamp": 1569262485349,
                    "message": {
                        "mid": "mid.echo",
                        "text": "Echo",
                        "is_echo": True,
                    },
                }
            ),
            WEBHOOK,
        )
        self.assertFalse(
            self.env["discuss.channel"].search([("gateway_id", "=", self.gateway.id)])
        )

    def test_deleted_posts_nothing(self):
        self.integrate_webhook()
        self.set_message(
            self._messaging_payload(
                {
                    "sender": {"id": IGSID},
                    "recipient": {"id": IGID},
                    "timestamp": 1569262485349,
                    "message": {
                        "mid": "mid.del",
                        "text": "Gone",
                        "is_deleted": True,
                    },
                }
            ),
            WEBHOOK,
        )
        self.assertFalse(
            self.env["discuss.channel"].search([("gateway_id", "=", self.gateway.id)])
        )

    def test_non_message_event_posts_nothing(self):
        self.integrate_webhook()
        self.set_message(
            self._messaging_payload(
                {
                    "sender": {"id": IGSID},
                    "recipient": {"id": IGID},
                    "timestamp": 1569262485349,
                    "read": {"mid": "mid.1"},
                }
            ),
            WEBHOOK,
        )
        self.assertFalse(
            self.env["discuss.channel"].search([("gateway_id", "=", self.gateway.id)])
        )

    def test_top_level_list_payload(self):
        chat = self.receive_message([self.text_message])
        self.assertEqual(len(chat), 1)
        comments = chat.message_ids.filtered(lambda m: m.message_type == "comment")
        self.assertEqual(len(comments), 1)

    @mute_logger("odoo.addons.mail_gateway.controllers.gateway")
    def test_verify_update_missing_header(self):
        self.integrate_webhook()
        self.set_message(self.text_message, WEBHOOK, headers=False)
        self.assertFalse(
            self.env["discuss.channel"].search([("gateway_id", "=", self.gateway.id)])
        )

    @mute_logger("odoo.addons.mail_gateway.controllers.gateway")
    def test_verify_update_wrong_signature(self):
        self.integrate_webhook()
        data = json.dumps(self.text_message)
        hex_dig = hmac.new(
            self.gateway.webhook_secret.encode(),
            data.encode(),
            hashlib.sha256,
        ).hexdigest()
        self.url_open(
            f"/gateway/{self.gateway.gateway_type}/{WEBHOOK}/update",
            data=data,
            headers={
                "Content-Type": "application/json",
                "x-hub-signature-256": f"sha256=dead{hex_dig}",
            },
        )
        self.assertFalse(
            self.env["discuss.channel"].search([("gateway_id", "=", self.gateway.id)])
        )

    @mute_logger("odoo.addons.mail_gateway.controllers.gateway")
    def test_verify_update_body_tampered(self):
        self.integrate_webhook()
        self.set_message(
            self.text_message,
            WEBHOOK,
            signature_body=json.dumps({"object": "instagram", "entry": []}),
        )
        self.assertFalse(
            self.env["discuss.channel"].search([("gateway_id", "=", self.gateway.id)])
        )

    def test_image_attachment_downloaded(self):
        self.requests_get.side_effect = self._mock_image_get
        payload = self._messaging_payload(
            {
                "sender": {"id": IGSID},
                "recipient": {"id": IGID},
                "timestamp": 1569262485349,
                "message": {
                    "mid": "mid.img",
                    "attachments": [
                        {
                            "type": "image",
                            "payload": {
                                "url": "https://lookaside.fbsbx.com/ig_messaging_cdn/?asset_id=1"
                            },
                        }
                    ],
                },
            }
        )
        chat = self.receive_message(payload)
        comments = chat.message_ids.filtered(lambda m: m.message_type == "comment")
        self.assertEqual(comments.attachment_ids.raw, b"JPEG")
        self.assertEqual(comments.attachment_ids.name, "image-0.jpg")

    def test_video_attachment_downloaded(self):
        self.requests_get.side_effect = self._mock_video_get
        payload = self._messaging_payload(
            {
                "sender": {"id": IGSID},
                "recipient": {"id": IGID},
                "timestamp": 1569262485349,
                "message": {
                    "mid": "mid.vid",
                    "attachments": [
                        {
                            "type": "video",
                            "payload": {
                                "url": "https://lookaside.fbsbx.com/ig_messaging_cdn/?asset_id=2"
                            },
                        }
                    ],
                },
            }
        )
        chat = self.receive_message(payload)
        comments = chat.message_ids.filtered(lambda m: m.message_type == "comment")
        self.assertEqual(comments.attachment_ids.raw, b"MP4V")
        self.assertEqual(comments.attachment_ids.name, "video-0.mp4")

    @mute_logger("odoo.addons.mail_gateway_instagram.models.mail_gateway_instagram")
    def test_attachment_exceeding_content_length_is_skipped(self):
        self.requests_get.side_effect = self._mock_oversized_attachment_get
        payload = self._messaging_payload(
            {
                "sender": {"id": IGSID},
                "recipient": {"id": IGID},
                "timestamp": 1569262485349,
                "message": {
                    "mid": "mid.huge",
                    "attachments": [
                        {
                            "type": "image",
                            "payload": {
                                "url": "https://lookaside.fbsbx.com/ig_messaging_cdn/?asset_id=9"
                            },
                        }
                    ],
                },
            }
        )
        chat = self.receive_message(payload)
        comments = chat.message_ids.filtered(lambda m: m.message_type == "comment")
        self.assertFalse(comments)

    def test_two_image_attachments_unique_names(self):
        self.requests_get.side_effect = self._mock_image_get
        payload = self._messaging_payload(
            {
                "sender": {"id": IGSID},
                "recipient": {"id": IGID},
                "timestamp": 1569262485349,
                "message": {
                    "mid": "mid.imgs",
                    "attachments": [
                        {
                            "type": "image",
                            "payload": {
                                "url": "https://lookaside.fbsbx.com/ig_messaging_cdn/?asset_id=1"
                            },
                        },
                        {
                            "type": "image",
                            "payload": {
                                "url": "https://lookaside.fbsbx.com/ig_messaging_cdn/?asset_id=2"
                            },
                        },
                    ],
                },
            }
        )
        chat = self.receive_message(payload)
        comments = chat.message_ids.filtered(lambda m: m.message_type == "comment")
        self.assertEqual(
            set(comments.attachment_ids.mapped("name")),
            {"image-0.jpg", "image-1.jpg"},
        )

    def test_inbound_text_markup_is_escaped(self):
        payload = self._messaging_payload(
            {
                "sender": {"id": IGSID},
                "recipient": {"id": IGID},
                "timestamp": 1569262485349,
                "message": {"mid": "mid.html", "text": "<b>Hello</b>"},
            }
        )
        chat = self.receive_message(payload)
        comments = chat.message_ids.filtered(lambda m: m.message_type == "comment")
        self.assertIn("&lt;b&gt;Hello&lt;/b&gt;", comments.body)
        self.assertNotIn("<b>Hello</b>", comments.body)

    def test_share_attachment_is_link_not_downloaded(self):
        share_url = "https://www.instagram.com/p/ABC123/"
        payload = self._messaging_payload(
            {
                "sender": {"id": IGSID},
                "recipient": {"id": IGID},
                "timestamp": 1569262485349,
                "message": {
                    "mid": "mid.share",
                    "attachments": [
                        {"type": "share", "payload": {"url": share_url}},
                    ],
                },
            }
        )
        chat = self.receive_message(payload)
        comments = chat.message_ids.filtered(lambda m: m.message_type == "comment")
        self.assertIn(share_url, comments.body)
        self.assertIn("<a ", comments.body)
        self.assertFalse(comments.attachment_ids)
        for call in self.requests_get.call_args_list:
            self.assertNotIn(share_url, call.args[0])

    def test_send_text(self):
        chat = self.receive_message(self.text_message)
        with patch(
            "odoo.addons.mail_gateway_instagram.models.mail_gateway_instagram.requests.post"
        ) as post_mock:
            response = MagicMock()
            response.raise_for_status.return_value = None
            response.json.return_value = {
                "recipient_id": IGSID,
                "message_id": "mid.out",
            }
            post_mock.return_value = response
            chat.message_post(
                body="Hello from Odoo",
                subtype_xmlid="mail.mt_comment",
                message_type="comment",
            )
        post_mock.assert_called_once()
        kwargs = post_mock.call_args.kwargs
        self.assertEqual(
            post_mock.call_args.args[0],
            f"https://graph.instagram.com/v26.0/{IGID}/messages",
        )
        self.assertEqual(
            kwargs["headers"]["Authorization"],
            f"Bearer {self.gateway.token}",
        )
        self.assertEqual(kwargs["json"]["recipient"], {"id": IGSID})
        self.assertEqual(kwargs["json"]["message"]["text"].strip(), "Hello from Odoo")
        self.assertEqual(kwargs["timeout"], 10)
        self.assertEqual(kwargs["proxies"], {})

    def test_send_failure_raises(self):
        chat = self.receive_message(self.text_message)
        message = chat.with_context(no_gateway_notification=True).message_post(
            body="Hello from Odoo",
            subtype_xmlid="mail.mt_comment",
            message_type="comment",
        )
        notification = self.env["mail.notification"].create(
            {
                "mail_message_id": message.id,
                "gateway_channel_id": chat.id,
                "notification_type": "gateway",
                "gateway_type": "instagram",
            }
        )
        with (
            patch(
                "odoo.addons.mail_gateway_instagram.models.mail_gateway_instagram.requests.post"
            ) as post_mock,
            mute_logger(
                "odoo.addons.mail_gateway_instagram.models.mail_gateway_instagram"
            ),
        ):
            post_mock.side_effect = requests.HTTPError("fail")
            with self.assertRaises(MailDeliveryException):
                self.env["mail.gateway.instagram"]._send(
                    self.gateway, notification, raise_exception=True
                )

    @mute_logger("odoo.addons.mail_gateway_instagram.models.mail_gateway_instagram")
    def test_send_graph_error_includes_response_body(self):
        chat = self.receive_message(self.text_message)
        fail = MagicMock()
        fail.ok = False
        fail.status_code = 400
        fail.reason = "Bad Request"
        fail.url = "https://graph.instagram.com/v26.0/x/messages"
        fail.text = (
            '{"error":{"message":"(#100) Invalid parameter '
            "https://example.com/mail_gateway_instagram/content/1/SECRET/a.png "
            'https://example.com/web/content/1/a.png?access_token=SECRET"}}'
        )
        with patch(
            "odoo.addons.mail_gateway_instagram.models.mail_gateway_instagram.requests.post"
        ) as post_mock:
            post_mock.return_value = fail
            mail_message = chat.message_post(
                body="Hello from Odoo",
                subtype_xmlid="mail.mt_comment",
                message_type="comment",
            )
        reason = self._gateway_notification(mail_message).failure_reason or ""
        self.assertIn("Invalid parameter", reason)
        self.assertIn("access_token=REDACTED", reason)
        self.assertIn("/mail_gateway_instagram/content/1/REDACTED", reason)
        self.assertNotIn("SECRET", reason)

    def test_robots_allows_instagram_content(self):
        response = self.url_open("/robots.txt")
        self.assertEqual(response.status_code, 200)
        self.assertIn("Allow: /mail_gateway_instagram/content", response.text)
        if "website" in self.env:
            return
        self.assertIn("User-agent: facebookexternalhit", response.text)
        allow_pos = response.text.find("Allow: /mail_gateway_instagram/content")
        disallow_pos = response.text.find("Disallow: /")
        self.assertLess(allow_pos, disallow_pos)

    def test_instagram_content_route_serves_file(self):
        chat = self.receive_message(self.text_message)
        attachment = self._create_channel_attachment(chat, "photo.png", raw=b"PNGDATA")
        token = attachment.generate_access_token()[0]
        response = self.url_open(
            f"/mail_gateway_instagram/content/{attachment.id}/{token}/photo.png"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b"PNGDATA")
        self.assertIn("image/png", response.headers.get("Content-Type", ""))

    def test_instagram_content_route_ogg_is_video_ogg(self):
        chat = self.receive_message(self.text_message)
        attachment = self._create_channel_attachment(chat, "clip.ogg", raw=b"OGG")
        token = attachment.generate_access_token()[0]
        response = self.url_open(
            f"/mail_gateway_instagram/content/{attachment.id}/{token}/clip.ogg"
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("video/ogg", response.headers.get("Content-Type", ""))

    def test_instagram_content_route_rejects_bad_token(self):
        chat = self.receive_message(self.text_message)
        attachment = self._create_channel_attachment(chat, "photo.png", raw=b"PNG")
        attachment.generate_access_token()
        response = self.url_open(
            f"/mail_gateway_instagram/content/{attachment.id}/not-the-token/photo.png"
        )
        self.assertEqual(response.status_code, 404)

    def _enable_own_messages(self):
        self.gateway.instagram_show_own_messages = True

    def _echo_item(self, recipient_id=IGSID, **message):
        item = {
            "sender": {"id": IGID},
            "timestamp": 1569262485349,
            "message": {
                "mid": "mid.echo",
                "text": "Echo",
                "is_echo": True,
                **message,
            },
        }
        if recipient_id is not None:
            item["recipient"] = {"id": recipient_id}
        return item

    def _graph_response(self, message_id):
        response = MagicMock()
        response.raise_for_status.return_value = None
        response.json.return_value = {
            "recipient_id": IGSID,
            "message_id": message_id,
        }
        return response

    def _gateway_notification(self, mail_message):
        return self.env["mail.notification"].search(
            [
                ("mail_message_id", "=", mail_message.id),
                ("notification_type", "=", "gateway"),
            ],
            limit=1,
        )

    def _comments(self, chat):
        return chat.message_ids.filtered(lambda m: m.message_type == "comment")

    def _create_channel_attachment(self, chat, name, raw=b"DATA", **vals):
        values = {
            "name": name,
            "raw": raw,
            "res_model": "discuss.channel",
            "res_id": chat.id,
        }
        values.update(vals)
        return self.env["ir.attachment"].create(values)

    def test_echo_with_setting_creates_channel_as_webhook_user(self):
        self._enable_own_messages()
        chat = self.receive_message(self._messaging_payload(self._echo_item()))
        self.assertEqual(len(chat), 1)
        self.assertEqual(chat.gateway_channel_token, IGSID)
        comments = self._comments(chat)
        self.assertEqual(len(comments), 1)
        self.assertEqual(comments.author_id, self.env.ref("base.user_root").partner_id)
        self.assertFalse(
            self.env["mail.guest"].search(
                [
                    ("gateway_id", "=", self.gateway.id),
                    ("gateway_token", "=", IGID),
                ]
            )
        )
        self.assertTrue(
            self.env["mail.guest"].search(
                [
                    ("gateway_id", "=", self.gateway.id),
                    ("gateway_token", "=", IGSID),
                ]
            )
        )

    def test_echo_with_setting_reuses_customer_channel(self):
        self._enable_own_messages()
        chat = self.receive_message(self.text_message)
        self.set_message(self._messaging_payload(self._echo_item()), WEBHOOK)
        chats = self.env["discuss.channel"].search(
            [("gateway_id", "=", self.gateway.id)]
        )
        self.assertEqual(chats, chat)
        comments = self._comments(chat)
        self.assertEqual(len(comments), 2)
        echo = comments.filtered(lambda m: "Echo" in (m.body or ""))
        self.assertEqual(len(echo), 1)
        self.assertEqual(echo.author_id, self.env.ref("base.user_root").partner_id)

    def test_echo_skips_when_mid_already_sent(self):
        self._enable_own_messages()
        chat = self.receive_message(self.text_message)
        with patch(
            "odoo.addons.mail_gateway_instagram.models.mail_gateway_instagram.requests.post"
        ) as post_mock:
            post_mock.return_value = self._graph_response("mid.out")
            chat.message_post(
                body="Hello from Odoo",
                subtype_xmlid="mail.mt_comment",
                message_type="comment",
            )
        comments_before = self._comments(chat)
        self.set_message(
            self._messaging_payload(
                self._echo_item(mid="mid.out", text="Hello from Odoo")
            ),
            WEBHOOK,
        )
        self.assertEqual(self._comments(chat), comments_before)

    def test_echo_skips_when_mid_in_instagram_sent_mids(self):
        self._enable_own_messages()
        chat = self.receive_message(self.text_message)
        first = self._create_channel_attachment(chat, "one.png", raw=b"PNG1")
        second = self._create_channel_attachment(chat, "two.png", raw=b"PNG2")
        with patch(
            "odoo.addons.mail_gateway_instagram.models.mail_gateway_instagram.requests.post"
        ) as post_mock:
            post_mock.side_effect = [
                self._graph_response("mid.a"),
                self._graph_response("mid.b"),
            ]
            mail_message = chat.message_post(
                body="",
                attachment_ids=[first.id, second.id],
                subtype_xmlid="mail.mt_comment",
                message_type="comment",
            )
        notification = self._gateway_notification(mail_message)
        self.assertEqual(notification.instagram_sent_mids, ["mid.a", "mid.b"])
        self.assertEqual(notification.gateway_message_id, "mid.b")
        comments_before = self._comments(chat)
        self.set_message(
            self._messaging_payload(
                self._echo_item(mid="mid.a", text="Should not appear")
            ),
            WEBHOOK,
        )
        self.assertEqual(self._comments(chat), comments_before)

    def test_echo_without_recipient_creates_nothing(self):
        self._enable_own_messages()
        self.integrate_webhook()
        self.set_message(
            self._messaging_payload(self._echo_item(recipient_id=None)),
            WEBHOOK,
        )
        self.assertFalse(
            self.env["discuss.channel"].search([("gateway_id", "=", self.gateway.id)])
        )

    def test_echo_with_setting_downloads_attachments(self):
        self._enable_own_messages()
        self.requests_get.side_effect = self._mock_image_get
        payload = self._messaging_payload(
            self._echo_item(
                text="",
                attachments=[
                    {
                        "type": "image",
                        "payload": {
                            "url": "https://lookaside.fbsbx.com/ig_messaging_cdn/?asset_id=1"
                        },
                    }
                ],
            )
        )
        chat = self.receive_message(payload)
        comments = self._comments(chat)
        self.assertEqual(len(comments), 1)
        self.assertEqual(comments.attachment_ids.raw, b"JPEG")
        self.assertEqual(comments.author_id, self.env.ref("base.user_root").partner_id)

    def test_deleted_posts_nothing_when_own_messages_enabled(self):
        self._enable_own_messages()
        self.integrate_webhook()
        self.set_message(
            self._messaging_payload(
                {
                    "sender": {"id": IGSID},
                    "recipient": {"id": IGID},
                    "timestamp": 1569262485349,
                    "message": {
                        "mid": "mid.del",
                        "text": "Gone",
                        "is_deleted": True,
                    },
                }
            ),
            WEBHOOK,
        )
        self.assertFalse(
            self.env["discuss.channel"].search([("gateway_id", "=", self.gateway.id)])
        )

    def test_send_url_link_without_footnotes(self):
        chat = self.receive_message(self.text_message)
        with patch(
            "odoo.addons.mail_gateway_instagram.models.mail_gateway_instagram.requests.post"
        ) as post_mock:
            post_mock.return_value = self._graph_response("mid.link")
            chat.message_post(
                body=Markup('<a href="https://miamapa.com/">https://miamapa.com/</a>'),
                subtype_xmlid="mail.mt_comment",
                message_type="comment",
            )
        text = post_mock.call_args.kwargs["json"]["message"]["text"]
        self.assertEqual(text.strip(), "https://miamapa.com/")

    def test_send_labelled_link_includes_href(self):
        chat = self.receive_message(self.text_message)
        with patch(
            "odoo.addons.mail_gateway_instagram.models.mail_gateway_instagram.requests.post"
        ) as post_mock:
            post_mock.return_value = self._graph_response("mid.link")
            chat.message_post(
                body=Markup('<a href="https://miamapa.com/">click here</a>'),
                subtype_xmlid="mail.mt_comment",
                message_type="comment",
            )
        text = post_mock.call_args.kwargs["json"]["message"]["text"]
        self.assertEqual(text.strip(), "click here (https://miamapa.com/)")

    def test_send_image_then_text_stores_both_mids(self):
        chat = self.receive_message(self.text_message)
        attachment = self._create_channel_attachment(chat, "photo.jpg", raw=b"JPEG")
        with patch(
            "odoo.addons.mail_gateway_instagram.models.mail_gateway_instagram.requests.post"
        ) as post_mock:
            post_mock.side_effect = [
                self._graph_response("mid.img"),
                self._graph_response("mid.txt"),
            ]
            mail_message = chat.message_post(
                body="Caption",
                attachment_ids=[attachment.id],
                subtype_xmlid="mail.mt_comment",
                message_type="comment",
            )
        self.assertEqual(post_mock.call_count, 2)
        image_payload = post_mock.call_args_list[0].kwargs["json"]["message"]
        self.assertIsInstance(image_payload["attachments"], list)
        self.assertEqual(image_payload["attachments"][0]["type"], "image")
        url = image_payload["attachments"][0]["payload"]["url"]
        self.assertIn(f"/mail_gateway_instagram/content/{attachment.id}/", url)
        self.assertIn(attachment.access_token, url)
        self.assertTrue(url.endswith("/photo.jpg"))
        self.assertNotIn("?", url)
        text_payload = post_mock.call_args_list[1].kwargs["json"]["message"]
        self.assertIn("Caption", text_payload["text"])
        notification = self._gateway_notification(mail_message)
        self.assertEqual(notification.instagram_sent_mids, ["mid.img", "mid.txt"])
        self.assertEqual(notification.gateway_message_id, "mid.txt")

    def test_send_image_commits_token_before_graph(self):
        chat = self.receive_message(self.text_message)
        attachment = self._create_channel_attachment(chat, "photo.png", raw=b"PNG")
        self.assertFalse(attachment.access_token)
        calls = []

        def fake_commit():
            calls.append("commit")

        def wrapped_post(*_args, **_kwargs):
            calls.append("post")
            return self._graph_response("mid.img")

        with (
            patch.object(self.env.registry, "in_test_mode", return_value=False),
            patch.object(self.env.cr, "commit", fake_commit),
            patch(
                "odoo.addons.mail_gateway_instagram.models.mail_gateway_instagram.requests.post",
                side_effect=wrapped_post,
            ),
        ):
            chat.message_post(
                body="",
                attachment_ids=[attachment.id],
                subtype_xmlid="mail.mt_comment",
                message_type="comment",
            )
        self.assertIn("commit", calls)
        self.assertIn("post", calls)
        self.assertLess(calls.index("commit"), calls.index("post"))
        self.assertTrue(attachment.access_token)

    @mute_logger("odoo.addons.mail_gateway_instagram.models.mail_gateway_instagram")
    def test_send_second_post_failure_stays_exception(self):
        chat = self.receive_message(self.text_message)
        attachment = self._create_channel_attachment(chat, "photo.png", raw=b"PNG")
        fail = MagicMock()
        fail.ok = False
        fail.status_code = 400
        fail.reason = "Bad Request"
        fail.url = "https://graph.instagram.com/v26.0/x/messages"
        fail.text = '{"error":{"message":"fail"}}'
        with patch(
            "odoo.addons.mail_gateway_instagram.models.mail_gateway_instagram.requests.post"
        ) as post_mock:
            post_mock.side_effect = [self._graph_response("mid.img"), fail]
            mail_message = chat.message_post(
                body="Caption",
                attachment_ids=[attachment.id],
                subtype_xmlid="mail.mt_comment",
                message_type="comment",
            )
        self.assertEqual(post_mock.call_count, 2)
        notification = self._gateway_notification(mail_message)
        self.assertEqual(notification.notification_status, "exception")
        self.assertEqual(notification.failure_type, "unknown")
        self.assertEqual(notification.instagram_sent_mids, ["mid.img"])
        self.assertEqual(notification.gateway_message_id, "mid.img")

    def test_send_attachment_filename_is_quoted(self):
        chat = self.receive_message(self.text_message)
        attachment = self._create_channel_attachment(chat, "a/b c.png", raw=b"PNG")
        with patch(
            "odoo.addons.mail_gateway_instagram.models.mail_gateway_instagram.requests.post"
        ) as post_mock:
            post_mock.return_value = self._graph_response("mid.img")
            chat.message_post(
                body="",
                attachment_ids=[attachment.id],
                subtype_xmlid="mail.mt_comment",
                message_type="comment",
            )
        url = post_mock.call_args.kwargs["json"]["message"]["attachments"][0][
            "payload"
        ]["url"]
        self.assertIn(f"/mail_gateway_instagram/content/{attachment.id}/", url)
        self.assertTrue(url.endswith("a%2Fb%20c.png"))
        self.assertNotIn("?", url)

    def test_send_two_attachments_oldest_first(self):
        chat = self.receive_message(self.text_message)
        first = self._create_channel_attachment(chat, "first.png", raw=b"ONE")
        second = self._create_channel_attachment(chat, "second.png", raw=b"TWO")
        self.assertLess(first.id, second.id)
        with patch(
            "odoo.addons.mail_gateway_instagram.models.mail_gateway_instagram.requests.post"
        ) as post_mock:
            post_mock.side_effect = [
                self._graph_response("mid.1"),
                self._graph_response("mid.2"),
            ]
            mail_message = chat.message_post(
                body="",
                attachment_ids=[second.id, first.id],
                subtype_xmlid="mail.mt_comment",
                message_type="comment",
            )
        self.assertEqual(post_mock.call_count, 2)
        first_url = post_mock.call_args_list[0].kwargs["json"]["message"][
            "attachments"
        ][0]["payload"]["url"]
        second_url = post_mock.call_args_list[1].kwargs["json"]["message"][
            "attachments"
        ][0]["payload"]["url"]
        self.assertIn(f"/mail_gateway_instagram/content/{first.id}/", first_url)
        self.assertIn(f"/mail_gateway_instagram/content/{second.id}/", second_url)
        notification = self._gateway_notification(mail_message)
        self.assertEqual(notification.instagram_sent_mids, ["mid.1", "mid.2"])
        self.assertEqual(notification.gateway_message_id, "mid.2")

    def test_send_pdf_uses_file_attachment_type(self):
        chat = self.receive_message(self.text_message)
        attachment = self._create_channel_attachment(chat, "doc.pdf", raw=b"%PDF")
        with patch(
            "odoo.addons.mail_gateway_instagram.models.mail_gateway_instagram.requests.post"
        ) as post_mock:
            post_mock.return_value = self._graph_response("mid.pdf")
            chat.message_post(
                body="",
                attachment_ids=[attachment.id],
                subtype_xmlid="mail.mt_comment",
                message_type="comment",
            )
        payload = post_mock.call_args.kwargs["json"]["message"]
        self.assertEqual(payload["attachment"]["type"], "file")
        self.assertNotIn("attachments", payload)

    def test_send_audio_extensions_use_audio_type(self):
        chat = self.receive_message(self.text_message)
        for name in ("clip.aac", "clip.m4a", "clip.wav"):
            attachment = self._create_channel_attachment(chat, name, raw=b"AUDIO")
            with patch(
                "odoo.addons.mail_gateway_instagram.models.mail_gateway_instagram.requests.post"
            ) as post_mock:
                post_mock.return_value = self._graph_response(f"mid.{name}")
                chat.message_post(
                    body="",
                    attachment_ids=[attachment.id],
                    subtype_xmlid="mail.mt_comment",
                    message_type="comment",
                )
            payload = post_mock.call_args.kwargs["json"]["message"]
            self.assertEqual(payload["attachment"]["type"], "audio")

    def test_send_ogg_is_video_with_canonical_mimetype(self):
        chat = self.receive_message(self.text_message)
        attachment = self._create_channel_attachment(chat, "clip.ogg", raw=b"OGG")
        with patch(
            "odoo.addons.mail_gateway_instagram.models.mail_gateway_instagram.requests.post"
        ) as post_mock:
            post_mock.return_value = self._graph_response("mid.ogg")
            chat.message_post(
                body="",
                attachment_ids=[attachment.id],
                subtype_xmlid="mail.mt_comment",
                message_type="comment",
            )
        payload = post_mock.call_args.kwargs["json"]["message"]
        self.assertEqual(payload["attachment"]["type"], "video")
        url = payload["attachment"]["payload"]["url"]
        self.assertTrue(url.endswith("/clip.ogg"))
        self.assertNotIn("?", url)

    @mute_logger("odoo.addons.mail_gateway_instagram.models.mail_gateway_instagram")
    def test_send_url_attachment_is_rejected(self):
        chat = self.receive_message(self.text_message)
        attachment = self.env["ir.attachment"].create(
            {
                "name": "photo.png",
                "type": "url",
                "url": "https://example.com/photo.png",
                "res_model": "discuss.channel",
                "res_id": chat.id,
            }
        )
        with patch(
            "odoo.addons.mail_gateway_instagram.models.mail_gateway_instagram.requests.post"
        ) as post_mock:
            mail_message = chat.message_post(
                body="",
                attachment_ids=[attachment.id],
                subtype_xmlid="mail.mt_comment",
                message_type="comment",
            )
        post_mock.assert_not_called()
        notification = self._gateway_notification(mail_message)
        self.assertEqual(notification.notification_status, "exception")

    @mute_logger("odoo.addons.mail_gateway_instagram.models.mail_gateway_instagram")
    def test_send_unsupported_type_is_rejected(self):
        chat = self.receive_message(self.text_message)
        cases = (
            ("notes.doc", b"DOC", "application/msword"),
            ("song.mp3", b"MP3", "audio/mpeg"),
        )
        for name, raw, mimetype in cases:
            attachment = self._create_channel_attachment(
                chat, name, raw=raw, mimetype=mimetype
            )
            with patch(
                "odoo.addons.mail_gateway_instagram.models.mail_gateway_instagram.requests.post"
            ) as post_mock:
                mail_message = chat.message_post(
                    body="Hi",
                    attachment_ids=[attachment.id],
                    subtype_xmlid="mail.mt_comment",
                    message_type="comment",
                )
            post_mock.assert_not_called()
            self.assertEqual(
                self._gateway_notification(mail_message).notification_status,
                "exception",
            )

    @mute_logger("odoo.addons.mail_gateway_instagram.models.mail_gateway_instagram")
    def test_send_mixed_valid_and_invalid_posts_nothing(self):
        chat = self.receive_message(self.text_message)
        valid = self._create_channel_attachment(chat, "ok.png", raw=b"PNG")
        invalid = self._create_channel_attachment(
            chat, "bad.doc", raw=b"DOC", mimetype="application/msword"
        )
        with patch(
            "odoo.addons.mail_gateway_instagram.models.mail_gateway_instagram.requests.post"
        ) as post_mock:
            mail_message = chat.message_post(
                body="Hi",
                attachment_ids=[valid.id, invalid.id],
                subtype_xmlid="mail.mt_comment",
                message_type="comment",
            )
        post_mock.assert_not_called()
        self.assertEqual(
            self._gateway_notification(mail_message).notification_status,
            "exception",
        )

    @mute_logger("odoo.addons.mail_gateway_instagram.models.mail_gateway_instagram")
    def test_send_oversize_image_is_rejected(self):
        chat = self.receive_message(self.text_message)
        attachment = self._create_channel_attachment(chat, "huge.jpg", raw=b"JPEG")
        self.env.cr.execute(
            "UPDATE ir_attachment SET file_size = %s WHERE id = %s",
            (INSTAGRAM_OUTBOUND_IMAGE_MAX_BYTES + 1, attachment.id),
        )
        attachment.invalidate_recordset(["file_size"])
        with patch(
            "odoo.addons.mail_gateway_instagram.models.mail_gateway_instagram.requests.post"
        ) as post_mock:
            mail_message = chat.message_post(
                body="Hi",
                attachment_ids=[attachment.id],
                subtype_xmlid="mail.mt_comment",
                message_type="comment",
            )
        post_mock.assert_not_called()
        self.assertEqual(
            self._gateway_notification(mail_message).notification_status,
            "exception",
        )

    @mute_logger("odoo.addons.mail_gateway_instagram.models.mail_gateway_instagram")
    def test_send_overlong_text_is_rejected(self):
        chat = self.receive_message(self.text_message)
        with patch(
            "odoo.addons.mail_gateway_instagram.models.mail_gateway_instagram.requests.post"
        ) as post_mock:
            mail_message = chat.message_post(
                body="a" * 1001,
                subtype_xmlid="mail.mt_comment",
                message_type="comment",
            )
        post_mock.assert_not_called()
        self.assertEqual(
            self._gateway_notification(mail_message).notification_status,
            "exception",
        )

    @mute_logger("odoo.addons.mail_gateway_instagram.models.mail_gateway_instagram")
    def test_send_media_with_overlong_text_posts_nothing(self):
        chat = self.receive_message(self.text_message)
        attachment = self._create_channel_attachment(chat, "ok.png", raw=b"PNG")
        with patch(
            "odoo.addons.mail_gateway_instagram.models.mail_gateway_instagram.requests.post"
        ) as post_mock:
            mail_message = chat.message_post(
                body="a" * 1001,
                attachment_ids=[attachment.id],
                subtype_xmlid="mail.mt_comment",
                message_type="comment",
            )
        post_mock.assert_not_called()
        self.assertEqual(
            self._gateway_notification(mail_message).notification_status,
            "exception",
        )

    def test_send_media_only_skips_text_post(self):
        chat = self.receive_message(self.text_message)
        attachment = self._create_channel_attachment(chat, "photo.png", raw=b"PNG")
        with patch(
            "odoo.addons.mail_gateway_instagram.models.mail_gateway_instagram.requests.post"
        ) as post_mock:
            post_mock.return_value = self._graph_response("mid.img")
            chat.message_post(
                body="   ",
                attachment_ids=[attachment.id],
                subtype_xmlid="mail.mt_comment",
                message_type="comment",
            )
        post_mock.assert_called_once()
        payload = post_mock.call_args.kwargs["json"]["message"]
        self.assertIn("attachments", payload)
        self.assertNotIn("text", payload)
