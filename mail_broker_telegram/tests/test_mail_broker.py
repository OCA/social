# Copyright 2021 Creu Blanca
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
import telegram
from mock import patch
from telegram.ext import ExtBot

from odoo.tests.common import TransactionCase


class MyBot(ExtBot):
    def _validate_token(self, *args, **kwargs):
        return

    def setWebhook(self, *args, **kwargs):
        return {}

    def get_webhook_info(self, *args, **kwargs):
        return telegram.WebhookInfo.de_json(
            {"pending_update_count": 0, "url": False, "has_custom_certificate": False},
            self,
        )


class TestMailBrokerController(TransactionCase):
    def setUp(self):
        super().setUp()
        self.webhook = "demo_hook"
        self.broker = self.env["mail.broker"].create(
            {"name": "broker", "broker_type": "telegram", "token": "token"}
        )
        self.password = "my_new_password"

    def test_webhook_cannot_set_webhook(self):
        self.assertFalse(self.broker.can_set_webhook)
        self.broker.set_webhook()
        self.assertFalse(self.broker.integrated_webhook)

    def test_webhook_management(self):
        self.broker.webhook_key = self.webhook
        self.broker.flush()
        self.assertTrue(self.broker.can_set_webhook)
        with patch.object(telegram, "Bot", MyBot):
            self.broker.set_webhook()
        self.assertTrue(self.broker.integrated_webhook)
        with patch.object(telegram, "Bot", MyBot):
            self.broker.update_webhook()
        self.assertTrue(self.broker.integrated_webhook)
        with patch.object(telegram, "Bot", MyBot):
            self.broker.remove_webhook()
        self.assertFalse(self.broker.integrated_webhook)
