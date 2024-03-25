# Copyright 2022 CreuBlanca
# Copyright 2024 Dixmit
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
import json
import time
from datetime import datetime
from unittest.mock import patch

import telegram
from telegram.ext import ExtBot

from odoo.tests.common import tagged

from odoo.addons.mail_broker.tests.common import MailBrokerTestCase


class MyBot(ExtBot):
    def _validate_token(self, *args, **kwargs):
        return

    async def initialize(self, *args, **kwargs):
        return

    async def setWebhook(self, *args, **kwargs):
        return {}

    async def get_webhook_info(self, *args, **kwargs):
        return telegram.WebhookInfo.de_json(
            {"pending_update_count": 0, "url": False, "has_custom_certificate": False},
            self,
        )

    async def get_chat(self, chat_id, *args, **kwargs):
        return telegram.Chat.de_json(
            {
                "id": chat_id,
                "type": "private",
            },
            self,
        )

    async def _send_message(self, endpoint, data, *args, **kwargs):
        return telegram.Message.de_json(
            {
                "date": time.mktime(datetime.now().timetuple()),
                "message_id": 1234,
                "chat": {
                    "id": data["chat_id"],
                    "type": "private",
                },
            },
            self,
        )


@tagged("-at_install", "post_install")
class TestMailBrokerTelegram(MailBrokerTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
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
        self.broker.flush_recordset()
        self.assertTrue(self.broker.can_set_webhook)
        with patch("telegram.Bot", MyBot):
            self.broker.set_webhook()
        self.assertEqual(self.broker.integrated_webhook_state, "integrated")
        with patch("telegram.Bot", MyBot):
            self.broker.update_webhook()
        self.assertEqual(self.broker.integrated_webhook_state, "integrated")
        with patch("telegram.Bot", MyBot):
            self.broker.remove_webhook()
        self.assertFalse(self.broker.integrated_webhook_state)

    def set_message(self, message, webhook):
        self.url_open(
            "/broker/{}/{}/update".format(self.broker.broker_type, webhook),
            data=json.dumps(message),
            headers={"Content-Type": "application/json"},
        )

    def test_webhook_unsecure_channel(self):

        self.broker.webhook_key = self.webhook
        self.broker.flush_recordset()
        self.assertTrue(self.broker.can_set_webhook)
        with patch("telegram.Bot", MyBot):
            self.broker.set_webhook()
        self.assertFalse(
            self.env["mail.channel"].search([("broker_id", "=", self.broker.id)])
        )

        with patch("telegram.Bot", ExtBot):
            self.set_message(self.message_01, self.webhook)
        chat = self.env["mail.channel"].search([("broker_id", "=", self.broker.id)])
        self.assertTrue(chat)
        self.assertTrue(chat.message_ids)

    def test_webhook_unsecure_channel_start(self):

        self.broker.webhook_key = self.webhook
        self.broker.flush_recordset()
        self.assertTrue(self.broker.can_set_webhook)
        with patch.object(telegram, "Bot", MyBot):
            self.broker.set_webhook()
        self.assertFalse(
            self.env["mail.channel"].search([("broker_id", "=", self.broker.id)])
        )
        with patch("telegram.Bot", ExtBot):
            self.set_message(self.message_02, self.webhook)
        chat = self.env["mail.channel"].search([("broker_id", "=", self.broker.id)])
        self.assertTrue(chat)
        self.assertFalse(chat.message_ids)
        with patch("telegram.Bot", MyBot):
            self.set_message(self.message_01, self.webhook)
        chat.invalidate_recordset()
        self.assertTrue(chat.message_ids)

    def test_webhook_secure_channel(self):

        self.broker.webhook_key = self.webhook
        self.broker.flush_recordset()
        self.assertTrue(self.broker.can_set_webhook)
        with patch.object(telegram, "Bot", MyBot):
            self.broker.set_webhook()
        self.broker.write(
            {"has_new_channel_security": True, "telegram_security_key": self.password}
        )
        self.broker.flush_recordset()
        self.assertFalse(
            self.env["mail.channel"].search([("broker_id", "=", self.broker.id)])
        )
        with patch("telegram.Bot", ExtBot):
            self.set_message(self.message_01, self.webhook)
        chat = self.env["mail.channel"].search([("broker_id", "=", self.broker.id)])
        self.assertFalse(chat)
        with patch("telegram.Bot", ExtBot):
            self.set_message(self.message_02, self.webhook)
        chat = self.env["mail.channel"].search([("broker_id", "=", self.broker.id)])
        self.assertFalse(chat)
        with patch("telegram.Bot", ExtBot):
            self.set_message(self.message_03, self.webhook)
        chat = self.env["mail.channel"].search([("broker_id", "=", self.broker.id)])
        self.assertFalse(chat)
        with patch("telegram.Bot", ExtBot):
            self.set_message(self.message_04, self.webhook)
        chat = self.env["mail.channel"].search([("broker_id", "=", self.broker.id)])
        self.assertTrue(chat)
        self.assertFalse(chat.message_ids)
        with patch("telegram.Bot", ExtBot):
            self.set_message(self.message_01, self.webhook)
        chat.invalidate_recordset()
        self.assertTrue(chat.message_ids)

    def test_webhook_no_webhook(self):
        self.assertFalse(
            self.env["mail.channel"].search([("broker_id", "=", self.broker.id)])
        )
        self.set_message(self.message_01, self.webhook + self.webhook)
        self.assertFalse(
            self.env["mail.channel"].search([("broker_id", "=", self.broker.id)])
        )

    def test_post_message(self):

        self.broker.webhook_key = self.webhook
        self.broker.flush_recordset()
        self.assertTrue(self.broker.can_set_webhook)
        with patch.object(telegram, "Bot", MyBot):
            self.broker.set_webhook()
        self.assertFalse(
            self.env["mail.channel"].search([("broker_id", "=", self.broker.id)])
        )
        with patch.object(telegram, "Bot", MyBot):
            self.set_message(self.message_02, self.webhook)
        channel = self.env["mail.channel"].search([("broker_id", "=", self.broker.id)])
        self.assertFalse(
            self.env["mail.notification"].search(
                [("broker_channel_id", "=", channel.id)]
            )
        )

        with patch.object(telegram, "Bot", MyBot):
            channel.message_post(
                # attachments=[("demo.png", b"IMAGE")],
                body="HELLO",
                subtype_xmlid="mail.mt_comment",
                message_type="comment",
            )
        self.assertTrue(
            self.env["mail.notification"].search(
                [("broker_channel_id", "=", channel.id)]
            )
        )
