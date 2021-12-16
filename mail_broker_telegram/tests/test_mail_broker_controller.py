# Copyright 2021 Creu Blanca
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from mock import patch
from telegram.ext import ExtBot

from odoo.tests.common import HOST, PORT, HttpCase


class TestMailBrokerController(HttpCase):
    def setUp(self):
        super().setUp()
        self.webhook = "demo_hook"
        self.broker = self.env["mail.broker"].create(
            {
                "name": "broker",
                "webhook_key": self.webhook,
                "broker_type": "telegram",
                "token": "token",
            }
        )
        self.password = "my_new_password"
        self.message_01 = {
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
        self.message_02 = {
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
        self.message_03 = {
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
                "text": "/start %s%s" % (self.password, self.password),
            },
        }
        self.message_04 = {
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
                "text": "/start %s" % self.password,
            },
        }

    def set_message(self, message, webhook):
        self.opener.post(
            "http://%s:%s/broker/%s/update" % (HOST, PORT, webhook), json=message
        )

    def test_webhook_unsecure_channel(self):
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
