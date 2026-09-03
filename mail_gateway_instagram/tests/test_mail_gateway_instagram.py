# Copyright 2026 Cetmix OÜ
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import hashlib
import hmac
import json
from datetime import datetime
from unittest.mock import MagicMock, patch

import requests

from odoo.tests.common import tagged
from odoo.tools import mute_logger

from odoo.addons.base.models.ir_mail_server import MailDeliveryException
from odoo.addons.mail_gateway.tests.common import MailGatewayTestCase
from odoo.addons.mail_gateway_instagram.models.mail_gateway_instagram import (
    INSTAGRAM_ATTACHMENT_MAX_BYTES,
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
