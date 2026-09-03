# Copyright 2026 Grupo Isonor - David Palanca
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import hashlib
import hmac
import json

from markupsafe import Markup

from odoo.tests.common import tagged

from odoo.addons.mail_gateway.tests.common import MailGatewayTestCase


@tagged("-at_install", "post_install")
class TestMailGatewayWhatsappMessageEcho(MailGatewayTestCase):
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
                "member_ids": [(4, cls.env.user.id)],
            }
        )
        cls.echo_message = {
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
                                "message_echoes": [
                                    {
                                        "from": "1234",
                                        "to": "34699999999",
                                        "id": "wamid.ECHO_ID",
                                        "timestamp": "1234",
                                        "type": "text",
                                        "text": {"body": "ECHO_BODY"},
                                    }
                                ],
                            },
                            "field": "smb_message_echoes",
                        }
                    ],
                }
            ],
        }

    def integrate_webhook(self):
        self.gateway.webhook_key = self.webhook
        self.gateway.set_webhook()
        self.url_open(
            "/gateway/{}/{}/update?hub.verify_token={}&hub.challenge={}".format(
                self.gateway.gateway_type,
                self.webhook,
                self.gateway.whatsapp_security_key,
                "22",
            ),
        )

    def set_message(self, message):
        data = json.dumps(message)
        hex_dig = hmac.new(
            self.gateway.webhook_secret.encode(),
            data.encode(),
            hashlib.sha256,
        ).hexdigest()
        self.url_open(
            f"/gateway/{self.gateway.gateway_type}/{self.webhook}/update",
            data=data,
            headers={
                "Content-Type": "application/json",
                "x-hub-signature-256": f"sha256={hex_dig}",
            },
        )

    def get_channel(self):
        return self.env["discuss.channel"].search(
            [("gateway_id", "=", self.gateway.id)]
        )

    def test_receive_message_echo(self):
        partner = self.env["res.partner"].create(
            {"name": "DEMO", "phone": "+34699999999"}
        )
        self.integrate_webhook()
        self.set_message(self.echo_message)
        chat = self.get_channel()
        self.assertEqual(chat.name, "DEMO")
        self.assertEqual(len(chat.message_ids), 1)
        self.assertEqual(chat.message_ids.body, Markup("<p>ECHO_BODY</p>"))
        # The agent is unknown, so the company answers on its behalf
        self.assertEqual(chat.message_ids.author_id, self.gateway.company_id.partner_id)
        self.assertNotEqual(chat.message_ids.author_id, partner)
        self.assertEqual(
            chat.message_ids.notification_ids.gateway_message_id, "wamid.ECHO_ID"
        )

    def test_receive_message_echo_unknown_partner(self):
        self.integrate_webhook()
        self.set_message(self.echo_message)
        chat = self.get_channel()
        self.assertEqual(chat.name, "34699999999")
        self.assertEqual(len(chat.message_ids), 1)

    def test_receive_message_echo_no_duplicates(self):
        self.integrate_webhook()
        self.set_message(self.echo_message)
        chat = self.get_channel()
        messages = chat.message_ids
        self.set_message(self.echo_message)
        self.assertEqual(chat.message_ids, messages)
