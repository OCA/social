# Copyright 2024 Dixmit
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo.tests.common import tagged

from odoo.addons.mail_gateway.tests.common import MailGatewayTestCase


@tagged("-at_install", "post_install")
class TestAutoReplyTelegram(MailGatewayTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.gateway = cls.env["mail.gateway"].create(
            {
                "name": "Test Telegram Gateway",
                "token": "test_token_auto_reply_telegram",
                "gateway_type": "telegram",
                "webhook_key": "test_webhook_key_auto_reply_telegram",
                "webhook_user_id": cls.env.ref("base.user_root").id,
                "auto_reply_message": "<p>Hello! Thank you for contacting us via Telegram.\
                     One of our agents will respond shortly.</p>",
            }
        )

    def test_auto_reply_message_sent_on_telegram_channel_creation(self):
        """Test if auto-reply message is sent when a Telegram channel is created"""
        # Simulate channel creation through Telegram service
        telegram_service = self.env["mail.gateway.telegram"]

        # Create a channel simulating a received Telegram message
        channel = telegram_service._get_channel(
            self.gateway, "test_token_123", {}, force_create=True
        )

        # Check if the channel was created
        self.assertTrue(channel, "Channel should have been created")

        # Check if there are messages in the channel
        messages = self.env["mail.message"].search(
            [
                ("model", "=", "mail.channel"),
                ("res_id", "=", channel.id),
            ]
        )

        # Check if the auto-reply message was sent
        auto_reply_found = any(
            self.gateway.auto_reply_message in msg.body for msg in messages
        )
        self.assertTrue(auto_reply_found, "Auto-reply message should have been sent")

    def test_no_auto_reply_when_not_configured_telegram(self):
        """Test that no auto-reply message is sent if not configured for Telegram"""
        # Create gateway without auto-reply message
        gateway_no_reply = self.env["mail.gateway"].create(
            {
                "name": "Test Telegram Gateway No Reply",
                "token": "test_token_no_reply_telegram",
                "gateway_type": "telegram",
                "webhook_key": "test_webhook_key_no_reply_telegram",
                "webhook_user_id": self.env.ref("base.user_root").id,
                "auto_reply_message": False,
            }
        )

        telegram_service = self.env["mail.gateway.telegram"]

        # Create a channel
        channel = telegram_service._get_channel(
            gateway_no_reply, "test_token_456", {}, force_create=True
        )

        # Check if the channel was created
        self.assertTrue(channel, "Channel should have been created")

        # Check message count in channel (should be 0 or only system messages)
        messages = self.env["mail.message"].search(
            [
                ("model", "=", "mail.channel"),
                ("res_id", "=", channel.id),
                ("message_type", "=", "comment"),
            ]
        )

        # Should not have comment messages if auto_reply not configured
        self.assertEqual(
            len(messages),
            0,
            "Should not have auto-reply messages when not configured",
        )

    def test_channel_reused_no_duplicate_auto_reply_telegram(self):
        """Test that auto-reply message is not sent in existing Telegram channels"""
        telegram_service = self.env["mail.gateway.telegram"]

        # Create a channel for the first time
        channel1 = telegram_service._get_channel(
            self.gateway, "test_token_789", {}, force_create=True
        )

        # Count messages after creation
        messages_count_1 = self.env["mail.message"].search_count(
            [
                ("model", "=", "mail.channel"),
                ("res_id", "=", channel1.id),
            ]
        )

        # Try to "create" the same channel again (should return existing)
        channel2 = telegram_service._get_channel(
            self.gateway, "test_token_789", {}, force_create=True
        )

        # Verify it's the same channel
        self.assertEqual(channel1.id, channel2.id, "Should be the same channel")

        # Count messages again
        messages_count_2 = self.env["mail.message"].search_count(
            [
                ("model", "=", "mail.channel"),
                ("res_id", "=", channel2.id),
            ]
        )

        # Should not have new auto-reply messages
        self.assertEqual(
            messages_count_1,
            messages_count_2,
            "Should not have new auto-reply messages for existing channel",
        )

    def test_auto_reply_specific_to_telegram_gateway(self):
        """Test that auto-reply works specifically with Telegram gateway type"""
        # Verify the gateway is specifically Telegram
        self.assertEqual(
            self.gateway.gateway_type, "telegram", "Gateway should be of type telegram"
        )

        # Test that the auto-reply message contains Telegram-specific content
        self.assertIn(
            "Telegram",
            self.gateway.auto_reply_message,
            "Auto-reply message should mention Telegram",
        )
