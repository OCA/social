# Copyright 2026 Anmol Garg
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from unittest.mock import patch

import requests

from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase, new_test_user
from odoo.tools import mute_logger


class TestTelegramBot(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Create a test bot
        cls.webhook_user = new_test_user(
            cls.env, login="webhook_user", groups="base.group_user"
        )
        cls.bot = cls.env["mail.gateway"].create(
            {
                "name": "Test Bot",
                "gateway_type": "telegram",
                "webhook_user_id": cls.webhook_user.id,
                "token": "123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11",
            }
        )
        # Create a test chat linked to the bot
        cls.chat = cls.env["telegram.chat"].create(
            {
                "name": "Test Chat",
                "chat_id": "1856618864",
                "gateway_id": cls.bot.id,
            }
        )

    @patch("requests.Session.post")
    def test_send_message_success(self, mock_post):
        """Test a successful message delivery"""
        # Mock a successful 200 response
        mock_post.return_value.status_code = 200
        mock_post.return_value.raise_for_status = lambda: None

        result = self.bot.send_message(self.chat.chat_id, "Hello from Odoo Test")

        self.assertTrue(result, "The send_message method should return True on success")
        self.assertEqual(
            mock_post.call_count, 1, "Exactly one POST request should be made"
        )

    def test_action_test_connection_no_chats(self):
        """Test action_test_connection raises UserError when no chats"""
        self.bot.telegram_chat_ids = [(5, 0, 0)]  # Clear chats
        with self.assertRaises(UserError):
            self.bot.action_test_connection()

    @patch("requests.Session.post")
    def test_action_test_connection_success(self, mock_post):
        """Test action_test_connection sends messages to all chats"""
        mock_post.return_value.status_code = 200
        mock_post.return_value.raise_for_status = lambda: None

        res = self.bot.action_test_connection()

        self.assertEqual(mock_post.call_count, 1)
        self.assertEqual(res.get("effect", {}).get("type"), "rainbow_man")

    @mute_logger("odoo.addons.mail_gateway_telegram_standalone.models.mail_gateway")
    @patch("requests.Session.post")
    def test_send_message_failure(self, mock_post):
        """Test handling of a connection failure"""
        # Simulate a real exception (like a timeout or DNS error)
        # This will trigger the 'except' block in your telegram_bot.py
        mock_post.side_effect = requests.exceptions.RequestException(
            "Connection Failed"
        )

        result = self.bot.send_message(self.chat.chat_id, "This should fail")

        # This should now correctly return False
        self.assertFalse(
            result, "The send_message method should return False on exception"
        )

    @patch("requests.get")
    def test_action_fetch_chats(self, mock_get):
        """Test fetching chats from Telegram API"""
        # Mock the JSON response from Telegram /getUpdates
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {
            "ok": True,
            "result": [
                {
                    "update_id": 1,
                    "message": {
                        "chat": {
                            "id": 111222,
                            "first_name": "NewUser",
                            "type": "private",
                        },
                        "text": "hi",
                    },
                }
            ],
        }

        self.bot.action_fetch_chats()

        # Verify a new chat was created in Odoo
        new_chat = self.env["telegram.chat"].search([("chat_id", "=", "111222")])
        self.assertTrue(
            new_chat, "A new chat should have been created from the mock data"
        )
        self.assertEqual(new_chat.name, "NewUser")

    @patch("requests.get")
    def test_action_fetch_chats_error(self, mock_get):
        """Test action_fetch_chats handles ok: False"""
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {"ok": False}
        result = self.bot.action_fetch_chats()
        self.assertFalse(result)

    @patch("requests.get")
    def test_action_fetch_chats_empty_message(self, mock_get):
        """Test action_fetch_chats handles result without message"""
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {
            "ok": True,
            "result": [{"update_id": 1}],  # No message key
        }
        result = self.bot.action_fetch_chats()
        self.assertTrue(result)

    @mute_logger("odoo.addons.mail_gateway_telegram_standalone.models.mail_gateway")
    @patch("requests.get")
    def test_action_fetch_chats_exception(self, mock_get):
        """Test action_fetch_chats handles exceptions"""
        mock_get.side_effect = requests.exceptions.RequestException("API Down")
        result = self.bot.action_fetch_chats()
        self.assertFalse(result)
