# Copyright 2022 CreuBlanca
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import hashlib
import hmac
import json
from unittest.mock import MagicMock, patch

from odoo.exceptions import UserError
from odoo.tests.common import tagged
from odoo.tools import mute_logger

from odoo.addons.mail_gateway.tests.common import MailGatewayTestCase


@tagged("-at_install", "post_install")
class TestMailGatewayTelegram(MailGatewayTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.webhook = "demo_hook"
        cls.gateway = cls.env["mail.gateway"].create(
            {
                "name": "gateway",
                "gateway_type": "whatsapp",
                "token": "token",
                "whatsapp_security_key": "key",
                "webhook_secret": "MY-SECRET",
            }
        )
        cls.partner = cls.env["res.partner"].create(
            {"name": "Partner", "mobile": "+34 600 000 000"}
        )
        cls.password = "my_new_password"
        cls.message_01 = {
            "object": "whatsapp_business_account",
            "entry": [
                {
                    "id": "WHATSAPP_BUSINESS_ACCOUNT_ID",
                    "changes": [
                        {
                            "value": {
                                "messaging_product": "whatsapp",
                                "metadata": {
                                    "display_phone_number": "1234",
                                    "phone_number_id": "34699999999",
                                },
                                "contacts": [
                                    {
                                        "profile": {"name": "NAME"},
                                        "wa_id": "34699999999",
                                    }
                                ],
                                "messages": [
                                    {
                                        "from": "34699999999",
                                        "id": "wamid.ID",
                                        "timestamp": "1234",
                                        "text": {"body": "MESSAGE_BODY"},
                                        "type": "text",
                                    }
                                ],
                            },
                            "field": "messages",
                        }
                    ],
                }
            ],
        }
        cls.message_02 = {
            "object": "whatsapp_business_account",
            "entry": [
                {
                    "id": "WHATSAPP_BUSINESS_ACCOUNT_ID",
                    "changes": [
                        {
                            "value": {
                                "messaging_product": "whatsapp",
                                "metadata": {
                                    "display_phone_number": "1234",
                                    "phone_number_id": "1234",
                                },
                                "contacts": [
                                    {"profile": {"name": "NAME"}, "wa_id": "1234"}
                                ],
                                "messages": [
                                    {
                                        "from": "1234",
                                        "id": "wamid.ID",
                                        "timestamp": "1234",
                                        "type": "image",
                                        "image": {
                                            "caption": "CAPTION",
                                            "mime_type": "image/jpeg",
                                            "sha256": "IMAGE_HASH",
                                            "id": "12356",
                                        },
                                    }
                                ],
                            },
                            "field": "messages",
                        }
                    ],
                }
            ],
        }

    def test_webhook_management(self):
        self.gateway.webhook_key = self.webhook
        self.assertTrue(self.gateway.can_set_webhook)
        self.gateway.set_webhook()
        self.assertEqual(self.gateway.integrated_webhook_state, "pending")
        self.gateway.remove_webhook()
        self.assertFalse(self.gateway.integrated_webhook_state)
        self.gateway.set_webhook()
        self.assertEqual(self.gateway.integrated_webhook_state, "pending")
        self.url_open(
            "/gateway/{}/{}/update?hub.verify_token={}&hub.challenge={}".format(
                self.gateway.gateway_type,
                self.webhook,
                self.gateway.whatsapp_security_key + "12",
                "22",
            ),
        )
        self.assertEqual(self.gateway.integrated_webhook_state, "pending")
        self.integrate_webhook()
        self.assertEqual(self.gateway.integrated_webhook_state, "integrated")
        self.gateway.remove_webhook()
        self.assertFalse(self.gateway.integrated_webhook_state)

    def integrate_webhook(self):
        self.url_open(
            "/gateway/{}/{}/update?hub.verify_token={}&hub.challenge={}".format(
                self.gateway.gateway_type,
                self.webhook,
                self.gateway.whatsapp_security_key,
                "22",
            ),
        )

    def set_message(self, message, webhook, headers=True):
        data = json.dumps(message)
        headers_dict = {"Content-Type": "application/json"}
        if headers:
            headers_dict["x-hub-signature-256"] = (
                "sha256=%s"
                % hmac.new(
                    self.gateway.webhook_secret.encode(),
                    data.encode(),
                    hashlib.sha256,
                ).hexdigest()
            )
        self.url_open(
            "/gateway/{}/{}/update".format(self.gateway.gateway_type, webhook),
            data=data,
            headers=headers_dict,
        )

    def receive_message(self, message):
        self.gateway.webhook_key = self.webhook
        self.gateway.set_webhook()
        self.integrate_webhook()
        self.set_message(message, self.webhook)
        chat = self.env["mail.channel"].search([("gateway_id", "=", self.gateway.id)])
        self.assertTrue(chat)
        self.assertTrue(chat.message_ids)
        return chat.message_ids

    def test_receive_message_01(self):
        message = self.receive_message(self.message_01)
        self.assertFalse(message.author_id)

    def test_receive_message_02(self):
        # Check that the partner is assigned automatically
        partner = self.env["res.partner"].create(
            {"name": "DEMO", "phone": "+34699999999"}
        )
        message = self.receive_message(self.message_01)
        self.assertEqual(message.author_id, partner)

    def test_receive_message_03(self):
        class GetImageResponse:
            def raise_for_status(self):
                pass

            def json(self):
                return {"url": "http://demo.url", "mime_type": "image/png"}

            content = b"binary_data"

        with patch("requests.get") as get_mock:
            get_mock.return_value = GetImageResponse()
            self.receive_message(self.message_02)

    def test_post_no_signature_no_message(self):
        self.gateway.webhook_key = self.webhook
        self.gateway.set_webhook()
        self.integrate_webhook()
        self.set_message(self.message_01, self.webhook, False)
        self.assertFalse(
            self.env["mail.channel"].search([("gateway_id", "=", self.gateway.id)])
        )

    def test_post_wrong_signature_no_message(self):
        self.gateway.webhook_key = self.webhook
        self.gateway.set_webhook()
        self.integrate_webhook()
        data = json.dumps(self.message_01)
        headers = {
            "Content-Type": "application/json",
            "x-hub-signature-256": (
                "sha256=1234%s"
                % hmac.new(
                    self.gateway.webhook_secret.encode(),
                    data.encode(),
                    hashlib.sha256,
                ).hexdigest()
            ),
        }
        self.url_open(
            "/gateway/{}/{}/update".format(self.gateway.gateway_type, self.webhook),
            data=data,
            headers=headers,
        )
        self.assertFalse(
            self.env["mail.channel"].search([("gateway_id", "=", self.gateway.id)])
        )

    def test_send_image(self):
        self.gateway.webhook_key = self.webhook
        self.gateway.set_webhook()
        self.integrate_webhook()
        composer = self.env["whatsapp.composer"].create(
            {
                "res_model": self.partner._name,
                "res_id": self.partner.id,
                "number_field_name": "mobile",
                "gateway_id": self.gateway.id,
            }
        )
        composer.action_view_whatsapp()
        channel = self.env["mail.channel"].search(
            [("gateway_id", "=", self.gateway.id)]
        )

        with patch("requests.post") as post_mock:
            post_mock.return_value = MagicMock()
            channel.message_post(
                attachments=[("demo.png", b"IMAGE")],
                subtype_xmlid="mail.mt_comment",
                message_type="comment",
            )
            post_mock.assert_called()
            self.assertEqual(post_mock.call_count, 2)

    def test_send_document_error(self):
        self.gateway.webhook_key = self.webhook
        self.gateway.set_webhook()
        self.integrate_webhook()
        composer = self.env["whatsapp.composer"].create(
            {
                "res_model": self.partner._name,
                "res_id": self.partner.id,
                "number_field_name": "mobile",
                "gateway_id": self.gateway.id,
            }
        )
        composer.action_view_whatsapp()
        channel = self.env["mail.channel"].search(
            [("gateway_id", "=", self.gateway.id)]
        )
        with mute_logger(
            "odoo.addons.mail_gateway_whatsapp.models.mail_gateway_whatsapp"
        ):
            message = channel.message_post(
                attachments=[("demo.xml", b"IMAGE")],
                subtype_xmlid="mail.mt_comment",
                message_type="comment",
            )
        self.assertEqual(message.notification_ids.notification_status, "exception")

    def test_compose(self):
        self.gateway.webhook_key = self.webhook
        self.gateway.set_webhook()
        self.integrate_webhook()
        composer = self.env["whatsapp.composer"].create(
            {
                "res_model": self.partner._name,
                "res_id": self.partner.id,
                "number_field_name": "mobile",
                "gateway_id": self.gateway.id,
            }
        )
        composer.action_view_whatsapp()
        channel = self.env["mail.channel"].search(
            [("gateway_id", "=", self.gateway.id)]
        )
        self.assertTrue(channel)
        self.assertFalse(channel.message_ids)
        with self.assertRaises(UserError):
            composer.action_send_whatsapp()
        composer.body = "DEMO"
        with patch("requests.post") as post_mock:
            post_mock.return_value = MagicMock()
            composer.action_send_whatsapp()
            post_mock.assert_called()
        channel.invalidate_recordset()
        self.assertTrue(channel.message_ids)
