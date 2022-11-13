# Copyright 2022 CreuBlanca
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import telegram
from mock import patch
from telegram.ext import ExtBot

from odoo.addons.mail_broker.tests.common import MailBrokerComponentRegistryTestCase


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


class TestMailBrokerTelegram(MailBrokerComponentRegistryTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls._load_module_components(cls, "mail_broker_telegram")
        cls.webhook = "demo_hook"
        cls.broker = cls.env["mail.broker"].create(
            {"name": "broker", "broker_type": "telegram", "token": "token"}
        )
        cls.password = "my_new_password"
        cls.message_01 = {
            "update_id": 1,
            "message": {
                "message_id": 1,
                "from": {
                    "id": 1,
                    "is_bot": False,
                    "first_name": "Demo",
                    "last_name": "Demo",
                    "language_code": "en",
                },
                "chat": {
                    "id": 1,
                    "first_name": "Demo",
                    "last_name": "Demo",
                    "type": "private",
                },
                "date": 1639666351,
                "text": "Hi Friend!",
            },
        }
        cls.message_02 = {
            "update_id": 1,
            "message": {
                "message_id": 2,
                "from": {
                    "id": 1,
                    "is_bot": False,
                    "first_name": "Demo",
                    "last_name": "Demo",
                    "language_code": "en",
                },
                "chat": {
                    "id": 1,
                    "first_name": "Demo",
                    "last_name": "Demo",
                    "type": "private",
                },
                "entities": [{"type": "bot_command", "offset": 0, "length": 6}],
                "date": 1639666351,
                "text": "/start",
            },
        }
        cls.message_03 = {
            "update_id": 1,
            "message": {
                "message_id": 3,
                "from": {
                    "id": 1,
                    "is_bot": False,
                    "first_name": "Demo",
                    "last_name": "Demo",
                    "language_code": "en",
                },
                "chat": {
                    "id": 1,
                    "first_name": "Demo",
                    "last_name": "Demo",
                    "type": "private",
                },
                "entities": [{"type": "bot_command", "offset": 0, "length": 6}],
                "date": 1639666351,
                "text": "/start %s%s" % (cls.password, cls.password),
            },
        }
        cls.message_04 = {
            "update_id": 1,
            "message": {
                "message_id": 4,
                "from": {
                    "id": 1,
                    "is_bot": False,
                    "first_name": "Demo",
                    "last_name": "Demo",
                    "language_code": "en",
                },
                "chat": {
                    "id": 1,
                    "first_name": "Demo",
                    "last_name": "Demo",
                    "type": "private",
                },
                "entities": [{"type": "bot_command", "offset": 0, "length": 6}],
                "date": 1639666351,
                "text": "/start %s" % cls.password,
            },
        }

    def test_webhook_management(self):
        self.broker.webhook_key = self.webhook
        self.broker.flush()
        self.assertTrue(self.broker.can_set_webhook)
        with patch.object(telegram, "Bot", MyBot):
            self.broker.set_webhook()
        self.assertEqual(self.broker.integrated_webhook_state, "integrated")
        with patch.object(telegram, "Bot", MyBot):
            self.broker.update_webhook()
        self.assertEqual(self.broker.integrated_webhook_state, "integrated")
        with patch.object(telegram, "Bot", MyBot):
            self.broker.remove_webhook()
        self.assertFalse(self.broker.integrated_webhook_state)

    def set_message(self, message, webhook):
        with self.broker.work_on(self.broker._name) as work:
            work.component(usage=self.broker.broker_type).post_update(
                webhook, **message
            )

    def test_webhook_unsecure_channel(self):

        self.broker.webhook_key = self.webhook
        self.broker.flush()
        self.assertTrue(self.broker.can_set_webhook)
        with patch.object(telegram, "Bot", MyBot):
            self.broker.set_webhook()
        self.assertFalse(
            self.env["mail.broker.channel"].search([("broker_id", "=", self.broker.id)])
        )
        slots = self.env["mail.broker"].broker_fetch_slot()
        for slot in slots:
            if slot["id"] == self.broker.id:
                break
        self.assertFalse(slot["threads"])

        with patch("telegram.Bot") as mck:
            mck.return_value = ExtBot
            self.set_message(self.message_01, self.webhook)
            mck.assert_called()
        chat = self.env["mail.broker.channel"].search(
            [("broker_id", "=", self.broker.id)]
        )
        self.assertTrue(chat)
        self.assertTrue(chat.message_ids)
        self.assertTrue(chat.message_fetch())
        slots = self.env["mail.broker"].broker_fetch_slot()
        for slot in slots:
            if slot["id"] == self.broker.id:
                break
        self.assertTrue(slot["threads"])
        self.assertTrue(self.broker.channel_search("Demo"))
        self.assertFalse(self.broker.channel_search("Not Demo"))

    def test_webhook_unsecure_channel_start(self):

        self.broker.webhook_key = self.webhook
        self.broker.flush()
        self.assertTrue(self.broker.can_set_webhook)
        with patch.object(telegram, "Bot", MyBot):
            self.broker.set_webhook()
        self.assertFalse(
            self.env["mail.broker.channel"].search([("broker_id", "=", self.broker.id)])
        )
        with patch("telegram.Bot") as mck:
            mck.return_value = ExtBot
            self.set_message(self.message_02, self.webhook)
            mck.assert_called()
        chat = self.env["mail.broker.channel"].search(
            [("broker_id", "=", self.broker.id)]
        )
        self.assertTrue(chat)
        self.assertFalse(chat.message_ids)
        self.assertFalse(chat.message_fetch())
        with patch("telegram.Bot") as mck:
            mck.return_value = ExtBot
            self.set_message(self.message_01, self.webhook)
            mck.assert_called()
        chat.refresh()
        self.assertTrue(chat.message_ids)

    def test_webhook_secure_channel(self):

        self.broker.webhook_key = self.webhook
        self.broker.flush()
        self.assertTrue(self.broker.can_set_webhook)
        with patch.object(telegram, "Bot", MyBot):
            self.broker.set_webhook()
        self.broker.write(
            {"has_new_channel_security": True, "telegram_security_key": self.password}
        )
        self.broker.flush()
        self.assertFalse(
            self.env["mail.broker.channel"].search([("broker_id", "=", self.broker.id)])
        )
        with patch("telegram.Bot") as mck:
            mck.return_value = ExtBot
            self.set_message(self.message_01, self.webhook)
            mck.assert_called()
        chat = self.env["mail.broker.channel"].search(
            [("broker_id", "=", self.broker.id)]
        )
        self.assertFalse(chat)

        with patch("telegram.Bot") as mck:
            mck.return_value = ExtBot
            self.set_message(self.message_02, self.webhook)
            mck.assert_called()
        chat = self.env["mail.broker.channel"].search(
            [("broker_id", "=", self.broker.id)]
        )
        self.assertFalse(chat)
        with patch("telegram.Bot") as mck:
            mck.return_value = ExtBot
            self.set_message(self.message_03, self.webhook)
            mck.assert_called()
        chat = self.env["mail.broker.channel"].search(
            [("broker_id", "=", self.broker.id)]
        )
        self.assertFalse(chat)
        with patch("telegram.Bot") as mck:
            mck.return_value = ExtBot
            self.set_message(self.message_04, self.webhook)
            mck.assert_called()
        chat = self.env["mail.broker.channel"].search(
            [("broker_id", "=", self.broker.id)]
        )
        self.assertTrue(chat)
        self.assertFalse(chat.message_ids)
        with patch("telegram.Bot") as mck:
            mck.return_value = ExtBot
            self.set_message(self.message_01, self.webhook)
            mck.assert_called()
        chat.refresh()
        self.assertTrue(chat.message_ids)

    def test_webhook_no_webhook(self):
        self.assertFalse(
            self.env["mail.broker.channel"].search([("broker_id", "=", self.broker.id)])
        )
        self.set_message(self.message_01, self.webhook + self.webhook)
        self.assertFalse(
            self.env["mail.broker.channel"].search([("broker_id", "=", self.broker.id)])
        )
