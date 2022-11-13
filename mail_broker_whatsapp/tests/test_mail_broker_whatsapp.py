# Copyright 2022 CreuBlanca
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import hashlib
import hmac

from mock import MagicMock, patch
from werkzeug.test import EnvironBuilder

from odoo import http
from odoo.exceptions import UserError
from odoo.http import HttpRequest, root

from odoo.addons.mail_broker.tests.common import MailBrokerComponentRegistryTestCase


class TestMailBrokerTelegram(MailBrokerComponentRegistryTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls._load_module_components(cls, "mail_broker_whatsapp")
        cls.webhook = "demo_hook"
        cls.broker = cls.env["mail.broker"].create(
            {
                "name": "broker",
                "broker_type": "whatsapp",
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

    def test_webhook_management(self):
        self.broker.webhook_key = self.webhook
        self.broker.flush()
        self.assertTrue(self.broker.can_set_webhook)
        self.broker.set_webhook()
        self.assertEqual(self.broker.integrated_webhook_state, "pending")
        self.broker.remove_webhook()
        self.assertFalse(self.broker.integrated_webhook_state)
        self.broker.set_webhook()
        self.assertEqual(self.broker.integrated_webhook_state, "pending")
        req = EnvironBuilder().get_request()
        root.setup_session(req)
        http._request_stack.push(HttpRequest(req))
        with self.broker.work_on(self.broker._name) as work:
            work.component(usage=self.broker.broker_type).get_update(
                self.webhook,
                **{
                    "hub": {
                        "verify_token": self.broker.whatsapp_security_key + "12",
                        "challenge": "22",
                    }
                }
            )
        http._request_stack.pop()
        self.assertEqual(self.broker.integrated_webhook_state, "pending")
        self.integrate_webhook()
        self.assertEqual(self.broker.integrated_webhook_state, "integrated")
        self.broker.remove_webhook()
        self.assertFalse(self.broker.integrated_webhook_state)

    def integrate_webhook(self):
        req = EnvironBuilder().get_request()
        root.setup_session(req)
        http._request_stack.push(HttpRequest(req))
        with self.broker.work_on(self.broker._name) as work:
            work.component(usage=self.broker.broker_type).get_update(
                self.webhook,
                **{
                    "hub": {
                        "verify_token": self.broker.whatsapp_security_key,
                        "challenge": "22",
                    }
                }
            )
        http._request_stack.pop()

    def set_message(self, message, webhook, headers=True):
        req = EnvironBuilder().get_request()
        root.setup_session(req)
        if headers:
            req.headers = {
                "x-hub-signature-256": "sha256=%s"
                % hmac.new(
                    self.broker.webhook_secret.encode(), req.data, hashlib.sha256,
                ).hexdigest()
            }
        http._request_stack.push(HttpRequest(req))
        with self.broker.work_on(self.broker._name) as work:
            work.component(usage=self.broker.broker_type).post_update(
                webhook, **message
            )
        http._request_stack.pop()

    def test_post_message(self):
        self.broker.webhook_key = self.webhook
        self.broker.set_webhook()
        self.integrate_webhook()
        self.set_message(self.message_01, self.webhook)
        self.assertTrue(
            self.env["mail.broker.channel"].search([("broker_id", "=", self.broker.id)])
        )

    def test_post_no_signature_no_message(self):
        self.broker.webhook_key = self.webhook
        self.broker.set_webhook()
        self.integrate_webhook()
        self.set_message(self.message_01, self.webhook, False)
        self.assertFalse(
            self.env["mail.broker.channel"].search([("broker_id", "=", self.broker.id)])
        )

    def test_post_wrong_signature_no_message(self):
        self.broker.webhook_key = self.webhook
        self.broker.set_webhook()
        self.integrate_webhook()
        req = EnvironBuilder().get_request()
        root.setup_session(req)
        req.headers = {
            "x-hub-signature-256": "sha256=1234%s"
            % hmac.new(
                self.broker.webhook_secret.encode(), req.data, hashlib.sha256,
            ).hexdigest()
        }
        http._request_stack.push(HttpRequest(req))
        with self.broker.work_on(self.broker._name) as work:
            work.component(usage=self.broker.broker_type).post_update(
                self.webhook, **self.message_01
            )
        http._request_stack.pop()
        self.assertFalse(
            self.env["mail.broker.channel"].search([("broker_id", "=", self.broker.id)])
        )

    def test_compose(self):
        self.broker.webhook_key = self.webhook
        self.broker.set_webhook()
        self.integrate_webhook()
        composer = self.env["whatsapp.composer"].create(
            {
                "res_model": self.partner._name,
                "res_id": self.partner.id,
                "number_field_name": "mobile",
            }
        )
        composer.action_view_whatsapp()
        channel = self.env["mail.broker.channel"].search(
            [("broker_id", "=", self.broker.id)]
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
        channel.refresh()
        self.assertTrue(channel.message_ids)
