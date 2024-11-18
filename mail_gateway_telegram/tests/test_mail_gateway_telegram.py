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
from odoo.tools import file_open, mute_logger

from odoo.addons.mail_gateway.tests.common import MailGatewayTestCase


class AttachmentFile:
    def __init__(self, file=False):
        self.file = file

    async def download_as_bytearray(self):
        if not self.file:
            return b"A" * 3138
        return file_open(self.file, mode="rb").read()


def getMyBot(message_id=1234, file=False):
    class MyBot(ExtBot):
        async def get_file(self, file_id, *args, **kwargs):
            return AttachmentFile(file)

        def _validate_token(self, *args, **kwargs):
            return

        async def initialize(self, *args, **kwargs):
            return

        async def setWebhook(self, *args, **kwargs):
            return {}

        async def get_webhook_info(self, *args, **kwargs):
            return telegram.WebhookInfo.de_json(
                {
                    "pending_update_count": 0,
                    "url": False,
                    "has_custom_certificate": False,
                },
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
                    "message_id": message_id,
                    "chat": {
                        "id": data["chat_id"],
                        "type": "private",
                    },
                },
                self,
            )

    return MyBot


@tagged("-at_install", "post_install")
class TestMailGatewayTelegram(MailGatewayTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.webhook = "demo_hook"
        cls.gateway = cls.env["mail.gateway"].create(
            {
                "name": "gateway",
                "gateway_type": "telegram",
                "token": "token",
                "member_ids": [(4, cls.env.user.id)],
            }
        )
        cls.password = "my_new_password"
        cls.gateway_token = "12341234"
        cls.message_01 = {
            "update_id": 1,
            "message": {
                "message_id": 1,
                "from": {
                    "id": cls.gateway_token,
                    "is_bot": False,
                    "first_name": "Demo",
                    "last_name": "Demo",
                    "language_code": "en",
                },
                "chat": {
                    "id": cls.gateway_token,
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
                    "id": cls.gateway_token,
                    "is_bot": False,
                    "first_name": "Demo",
                    "last_name": "Demo",
                    "language_code": "en",
                },
                "chat": {
                    "id": cls.gateway_token,
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
                    "id": cls.gateway_token,
                    "is_bot": False,
                    "first_name": "Demo",
                    "last_name": "Demo",
                    "language_code": "en",
                },
                "chat": {
                    "id": cls.gateway_token,
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
                    "id": cls.gateway_token,
                    "is_bot": False,
                    "first_name": "Demo",
                    "last_name": "Demo",
                    "language_code": "en",
                },
                "chat": {
                    "id": cls.gateway_token,
                    "first_name": "Demo",
                    "last_name": "Demo",
                    "type": "private",
                },
                "entities": [{"type": "bot_command", "offset": 0, "length": 6}],
                "date": 1639666351,
                "text": "/start %s" % cls.password,
            },
        }
        cls.message_05 = {
            "update_id": 5,
            "message": {
                "message_id": 5,
                "from": {
                    "id": cls.gateway_token,
                    "is_bot": False,
                    "first_name": "Demo",
                    "last_name": "Demo",
                    "language_code": "en",
                },
                "chat": {
                    "id": cls.gateway_token,
                    "first_name": "Demo",
                    "last_name": "Demo",
                    "type": "private",
                },
                "date": 1639666351,
                "document": {
                    "title": "icon.svg",
                    "file_name": "icon.svg",
                    "mime_type": "image/svg+xml",
                    "file_id": "MY_FILE_ID",
                    "file_unique_id": "MY_FILE_UNIQUe_ID",
                    "file_size": 3138,
                },
            },
        }
        cls.reply_to_message_id = 500
        cls.message_06 = {
            "update_id": 1,
            "message": {
                "message_id": 6,
                "from": {
                    "id": cls.gateway_token,
                    "is_bot": False,
                    "first_name": "Demo",
                    "last_name": "Demo",
                    "language_code": "en",
                },
                "chat": {
                    "id": cls.gateway_token,
                    "first_name": "Demo",
                    "last_name": "Demo",
                    "type": "private",
                },
                "reply_to_message": {
                    "message_id": cls.reply_to_message_id,
                    "from": {
                        "id": cls.gateway_token,
                        "is_bot": False,
                        "first_name": "Demo",
                        "last_name": "Demo",
                        "language_code": "en",
                    },
                    "chat": {
                        "id": cls.gateway_token,
                        "first_name": "Demo",
                        "last_name": "Demo",
                        "type": "private",
                    },
                    "date": 1639666351,
                },
                "date": 1639666351,
                "text": "What do you want to do?",
            },
        }

        cls.message_07 = {
            "update_id": 7,
            "message": {
                "message_id": 7,
                "from": {
                    "id": cls.gateway_token,
                    "is_bot": False,
                    "first_name": "Demo",
                    "last_name": "Demo",
                    "language_code": "en",
                },
                "chat": {
                    "id": cls.gateway_token,
                    "first_name": "Demo",
                    "last_name": "Demo",
                    "type": "private",
                },
                "date": 1639666351,
                "sticker": {
                    "width": 512,
                    "height": 512,
                    "emoji": "����",
                    "set_name": "DrugStore",
                    "is_animated": True,
                    "is_video": False,
                    "type": "regular",
                    "thumbnail": {
                        "file_id": "FILE_ID",
                        "file_unique_id": "FILE_UNIQUE_ID",
                        "file_size": 4662,
                        "width": 128,
                        "height": 128,
                    },
                    "thumb": {
                        "file_id": "FILE_ID",
                        "file_unique_id": "FILE_UNIQUE_ID",
                        "file_size": 4662,
                        "width": 128,
                        "height": 128,
                    },
                    "file_id": "FILE_ID",
                    "file_unique_id": "FILE_UNIQUE_ID",
                    "file_size": 10094,
                },
            },
        }
        cls.partner = cls.env["res.partner"].create({"name": "Demo"})

    def test_webhook_management(self):
        self.gateway.webhook_key = self.webhook
        self.gateway.flush_recordset()
        self.assertTrue(self.gateway.can_set_webhook)
        with patch("telegram.Bot", getMyBot()):
            self.gateway.set_webhook()
        self.assertEqual(self.gateway.integrated_webhook_state, "integrated")
        with patch("telegram.Bot", getMyBot()):
            self.gateway.update_webhook()
        self.assertEqual(self.gateway.integrated_webhook_state, "integrated")
        with patch("telegram.Bot", getMyBot()):
            self.gateway.remove_webhook()
        self.assertFalse(self.gateway.integrated_webhook_state)

    def set_message(self, message, webhook, timeout=12):
        self.url_open(
            "/gateway/{}/{}/update".format(self.gateway.gateway_type, webhook),
            data=json.dumps(message),
            headers={"Content-Type": "application/json"},
            timeout=timeout,
            # We need to increase the timeout to avoid the test to fail on sticker....
        )

    def test_webhook_unsecure_channel(self):

        self.gateway.webhook_key = self.webhook
        self.gateway.flush_recordset()
        self.assertTrue(self.gateway.can_set_webhook)
        with patch("telegram.Bot", getMyBot()):
            self.gateway.set_webhook()
        self.assertFalse(
            self.env["mail.channel"].search([("gateway_id", "=", self.gateway.id)])
        )

        with patch("telegram.Bot", ExtBot):
            self.set_message(self.message_01, self.webhook)
        chat = self.env["mail.channel"].search([("gateway_id", "=", self.gateway.id)])
        self.assertTrue(chat)
        self.assertTrue(chat.message_ids)

    def test_webhook_unsecure_channel_start(self):

        self.gateway.webhook_key = self.webhook
        self.gateway.flush_recordset()
        self.assertTrue(self.gateway.can_set_webhook)
        with patch.object(telegram, "Bot", getMyBot()):
            self.gateway.set_webhook()
        self.assertFalse(
            self.env["mail.channel"].search([("gateway_id", "=", self.gateway.id)])
        )
        with patch("telegram.Bot", ExtBot):
            self.set_message(self.message_02, self.webhook)
        chat = self.env["mail.channel"].search([("gateway_id", "=", self.gateway.id)])
        self.assertTrue(chat)
        self.assertFalse(chat.message_ids)
        with patch("telegram.Bot", getMyBot()):
            self.set_message(self.message_01, self.webhook)
        chat.invalidate_recordset()
        self.assertTrue(chat.message_ids)

    def test_webhook_secure_channel(self):

        self.gateway.webhook_key = self.webhook
        self.gateway.flush_recordset()
        self.assertTrue(self.gateway.can_set_webhook)
        with patch.object(telegram, "Bot", getMyBot()):
            self.gateway.set_webhook()
        self.gateway.write(
            {"has_new_channel_security": True, "telegram_security_key": self.password}
        )
        self.gateway.flush_recordset()
        self.assertFalse(
            self.env["mail.channel"].search([("gateway_id", "=", self.gateway.id)])
        )
        with patch("telegram.Bot", ExtBot):
            self.set_message(self.message_01, self.webhook)
        chat = self.env["mail.channel"].search([("gateway_id", "=", self.gateway.id)])
        self.assertFalse(chat)
        with patch("telegram.Bot", ExtBot):
            self.set_message(self.message_02, self.webhook)
        chat = self.env["mail.channel"].search([("gateway_id", "=", self.gateway.id)])
        self.assertFalse(chat)
        with patch("telegram.Bot", ExtBot):
            self.set_message(self.message_03, self.webhook)
        chat = self.env["mail.channel"].search([("gateway_id", "=", self.gateway.id)])
        self.assertFalse(chat)
        with patch("telegram.Bot", ExtBot):
            self.set_message(self.message_04, self.webhook)
        chat = self.env["mail.channel"].search([("gateway_id", "=", self.gateway.id)])
        self.assertTrue(chat)
        self.assertFalse(chat.message_ids)
        with patch("telegram.Bot", ExtBot):
            self.set_message(self.message_01, self.webhook)
        chat.invalidate_recordset()
        self.assertTrue(chat.message_ids)

    def test_webhook_no_webhook(self):
        self.assertFalse(
            self.env["mail.channel"].search([("gateway_id", "=", self.gateway.id)])
        )
        self.set_message(self.message_01, self.webhook + self.webhook)
        self.assertFalse(
            self.env["mail.channel"].search([("gateway_id", "=", self.gateway.id)])
        )

    def test_post_message(self):
        self.gateway.webhook_key = self.webhook
        self.gateway.flush_recordset()
        self.assertTrue(self.gateway.can_set_webhook)
        with patch.object(telegram, "Bot", getMyBot()):
            self.gateway.set_webhook()
        self.assertFalse(
            self.env["mail.channel"].search([("gateway_id", "=", self.gateway.id)])
        )
        with patch.object(telegram, "Bot", getMyBot()):
            self.set_message(self.message_02, self.webhook)
        channel = self.env["mail.channel"].search(
            [("gateway_id", "=", self.gateway.id)]
        )
        self.assertFalse(
            self.env["mail.notification"].search(
                [("gateway_channel_id", "=", channel.id)]
            )
        )
        with patch.object(telegram, "Bot", getMyBot()):
            channel.message_post(
                body="HELLO",
                subtype_xmlid="mail.mt_comment",
                message_type="comment",
            )
        self.assertTrue(
            self.env["mail.notification"].search(
                [("gateway_channel_id", "=", channel.id)]
            )
        )

    def test_post_message_image(self):
        self.gateway.webhook_key = self.webhook
        self.gateway.flush_recordset()
        self.assertTrue(self.gateway.can_set_webhook)
        with patch.object(telegram, "Bot", getMyBot()):
            self.gateway.set_webhook()
        self.assertFalse(
            self.env["mail.channel"].search([("gateway_id", "=", self.gateway.id)])
        )
        with patch.object(telegram, "Bot", getMyBot()):
            self.set_message(self.message_02, self.webhook)
        channel = self.env["mail.channel"].search(
            [("gateway_id", "=", self.gateway.id)]
        )
        self.assertFalse(
            self.env["mail.notification"].search(
                [("gateway_channel_id", "=", channel.id)]
            )
        )
        with patch.object(telegram, "Bot", getMyBot()):
            channel.message_post(
                attachments=[("demo.png", b"IMAGE")],
                subtype_xmlid="mail.mt_comment",
                message_type="comment",
            )
        self.assertTrue(
            self.env["mail.notification"].search(
                [("gateway_channel_id", "=", channel.id)]
            )
        )

    def test_post_message_error(self):
        self.gateway.webhook_key = self.webhook
        self.gateway.flush_recordset()
        self.assertTrue(self.gateway.can_set_webhook)
        with patch.object(telegram, "Bot", getMyBot()):
            self.gateway.set_webhook()
        self.assertFalse(
            self.env["mail.channel"].search([("gateway_id", "=", self.gateway.id)])
        )
        with patch.object(telegram, "Bot", getMyBot()):
            self.set_message(self.message_02, self.webhook)
        channel = self.env["mail.channel"].search(
            [("gateway_id", "=", self.gateway.id)]
        )
        self.assertFalse(
            self.env["mail.notification"].search(
                [("gateway_channel_id", "=", channel.id)]
            )
        )
        with mute_logger(
            "odoo.addons.mail_gateway_telegram.models.mail_gateway_telegram"
        ):
            channel.message_post(
                body="My message",
                subtype_xmlid="mail.mt_comment",
                message_type="comment",
            )
        notification = self.env["mail.notification"].search(
            [("gateway_channel_id", "=", channel.id)]
        )
        self.assertTrue(notification)
        self.assertEqual(notification.notification_status, "exception")

    def test_post_message_document(self):
        self.gateway.webhook_key = self.webhook
        self.gateway.flush_recordset()
        self.assertTrue(self.gateway.can_set_webhook)
        with patch.object(telegram, "Bot", getMyBot()):
            self.gateway.set_webhook()
        self.assertFalse(
            self.env["mail.channel"].search([("gateway_id", "=", self.gateway.id)])
        )
        with patch.object(telegram, "Bot", getMyBot()):
            self.set_message(self.message_02, self.webhook)
        channel = self.env["mail.channel"].search(
            [("gateway_id", "=", self.gateway.id)]
        )
        self.assertFalse(
            self.env["mail.notification"].search(
                [("gateway_channel_id", "=", channel.id)]
            )
        )
        with patch.object(telegram, "Bot", getMyBot()):
            channel.message_post(
                attachments=[("application/pdf", b"PDF")],
                subtype_xmlid="mail.mt_comment",
                message_type="comment",
            )
        self.assertTrue(
            self.env["mail.notification"].search(
                [("gateway_channel_id", "=", channel.id)]
            )
        )

    def test_webhook_attachment(self):
        self.gateway.webhook_key = self.webhook
        self.gateway.flush_recordset()
        self.assertTrue(self.gateway.can_set_webhook)
        with patch("telegram.Bot", getMyBot()):
            self.gateway.set_webhook()
        self.assertFalse(
            self.env["mail.channel"].search([("gateway_id", "=", self.gateway.id)])
        )
        with patch("telegram.Bot", getMyBot()):
            self.set_message(self.message_05, self.webhook)
        chat = self.env["mail.channel"].search([("gateway_id", "=", self.gateway.id)])
        self.assertTrue(chat)
        self.assertTrue(chat.message_ids)
        self.assertTrue(chat.message_ids.attachment_ids)

    def test_webhook_sticker(self):
        self.gateway.webhook_key = self.webhook
        self.gateway.flush_recordset()
        self.assertTrue(self.gateway.can_set_webhook)
        with patch("telegram.Bot", getMyBot()):
            self.gateway.set_webhook()
        self.assertFalse(
            self.env["mail.channel"].search([("gateway_id", "=", self.gateway.id)])
        )
        with patch(
            "telegram.Bot",
            getMyBot(file="addons/mail_gateway_telegram/tests/sticker.tgs"),
        ):
            self.set_message(self.message_07, self.webhook, timeout=30)
        chat = self.env["mail.channel"].search([("gateway_id", "=", self.gateway.id)])
        self.assertTrue(chat)
        self.assertTrue(chat.message_ids)
        self.assertTrue(chat.message_ids.attachment_ids)

    def test_webhook_reply(self):
        self.gateway.webhook_key = self.webhook
        self.gateway.flush_recordset()
        self.assertTrue(self.gateway.can_set_webhook)
        with patch("telegram.Bot", getMyBot()):
            self.gateway.set_webhook()
        with patch.object(telegram, "Bot", getMyBot()):
            self.set_message(self.message_02, self.webhook)

        channel = self.env["mail.channel"].search(
            [("gateway_id", "=", self.gateway.id)]
        )
        self.assertFalse(
            self.env["mail.notification"].search(
                [("gateway_channel_id", "=", channel.id)]
            )
        )
        # Assign the partner to the channel
        self.env["mail.guest.manage"].create(
            {
                "partner_id": self.partner.id,
                "guest_id": self.env["mail.guest"]
                .search(
                    [
                        ("gateway_token", "=", self.gateway_token),
                        ("gateway_id", "=", self.gateway.id),
                    ]
                )
                .id,
            }
        ).merge_partner()
        self.assertTrue(self.partner.gateway_channel_ids)
        with patch.object(telegram, "Bot", getMyBot(self.reply_to_message_id)):
            new_message = self.partner.message_post(
                body="HELLO",
                subtype_xmlid="mail.mt_comment",
                message_type="comment",
                gateway_notifications=[
                    {
                        "channel_type": "gateway",
                        "gateway_channel_id": self.partner.gateway_channel_ids.id,
                        "partner_id": self.partner.id,
                    }
                ],
            )
        self.assertTrue(new_message.gateway_message_ids)
        self.partner.invalidate_recordset()
        messages = self.partner.message_ids
        with patch.object(telegram, "Bot", getMyBot()):
            self.set_message(self.message_06, self.webhook)
        # The message should be assigned the the partner
        self.partner.invalidate_recordset()
        self.assertTrue(self.partner.message_ids - messages)

    def test_webhook_reply_new_partner(self):
        self.gateway.webhook_key = self.webhook
        self.gateway.flush_recordset()
        self.assertTrue(self.gateway.can_set_webhook)
        with patch("telegram.Bot", getMyBot()):
            self.gateway.set_webhook()
        with patch.object(telegram, "Bot", getMyBot()):
            self.set_message(self.message_02, self.webhook)

        channel = self.env["mail.channel"].search(
            [("gateway_id", "=", self.gateway.id)]
        )
        self.assertFalse(
            self.env["mail.notification"].search(
                [("gateway_channel_id", "=", channel.id)]
            )
        )
        # Assign the partner to the channel
        partner_action = (
            self.env["mail.guest.manage"]
            .create(
                {
                    "guest_id": self.env["mail.guest"]
                    .search(
                        [
                            ("gateway_token", "=", self.gateway_token),
                            ("gateway_id", "=", self.gateway.id),
                        ]
                    )
                    .id,
                }
            )
            .create_partner()
        )
        partner = self.env[partner_action["res_model"]].browse(partner_action["res_id"])
        self.assertTrue(partner.gateway_channel_ids)
        with patch.object(telegram, "Bot", getMyBot(self.reply_to_message_id)):
            new_message = partner.message_post(
                body="HELLO",
                subtype_xmlid="mail.mt_comment",
                message_type="comment",
                gateway_notifications=[
                    {
                        "channel_type": "gateway",
                        "gateway_channel_id": partner.gateway_channel_ids.id,
                        "partner_id": partner.id,
                    }
                ],
            )
        self.assertTrue(new_message.gateway_message_ids)
        partner.invalidate_recordset()
        messages = partner.message_ids
        with patch.object(telegram, "Bot", getMyBot()):
            self.set_message(self.message_06, self.webhook)
        # The message should be assigned the the partner
        partner.invalidate_recordset()
        self.assertTrue(partner.message_ids - messages)

    def test_link_mail_message(self):
        self.gateway.webhook_key = self.webhook
        self.gateway.flush_recordset()
        self.assertTrue(self.gateway.can_set_webhook)
        with patch("telegram.Bot", getMyBot()):
            self.gateway.set_webhook()
        with patch.object(telegram, "Bot", getMyBot()):
            self.set_message(self.message_01, self.webhook)
        messages = self.partner.message_ids
        channel = self.env["mail.channel"].search(
            [("gateway_id", "=", self.gateway.id)]
        )
        self.assertTrue(channel.message_ids)
        self.env["mail.message.gateway.link"].create(
            {
                "message_id": channel.message_ids.id,
                "resource_ref": "{},{}".format(self.partner._name, self.partner.id),
            }
        ).link_message()
        self.assertTrue(self.partner.message_ids - messages)

    def test_send_mail_message(self):
        self.gateway.webhook_key = self.webhook
        self.gateway.flush_recordset()
        self.assertTrue(self.gateway.can_set_webhook)
        with patch("telegram.Bot", getMyBot()):
            self.gateway.set_webhook()
        with patch.object(telegram, "Bot", getMyBot()):
            self.set_message(self.message_01, self.webhook)

        channel = self.env["mail.channel"].search(
            [("gateway_id", "=", self.gateway.id)]
        )
        self.assertFalse(
            self.env["mail.notification"].search(
                [("gateway_channel_id", "=", channel.id)]
            )
        )
        # Assign the partner to the channel
        partner_action = (
            self.env["mail.guest.manage"]
            .create(
                {
                    "guest_id": self.env["mail.guest"]
                    .search(
                        [
                            ("gateway_token", "=", self.gateway_token),
                            ("gateway_id", "=", self.gateway.id),
                        ]
                    )
                    .id,
                }
            )
            .create_partner()
        )
        partner = self.env[partner_action["res_model"]].browse(partner_action["res_id"])
        message = partner.message_post(body="HELLO")
        self.assertFalse(
            self.env["mail.notification"].search(
                [("gateway_channel_id", "=", channel.id)]
            )
        )
        with patch.object(telegram, "Bot", getMyBot()):
            self.env["mail.message.gateway.send"].create(
                {
                    "message_id": message.id,
                    "partner_id": partner.id,
                    "gateway_channel_id": partner.gateway_channel_ids.id,
                }
            ).send()
        self.assertTrue(
            self.env["mail.notification"].search(
                [("gateway_channel_id", "=", channel.id)]
            )
        )

    def test_channel(self):
        self.gateway.webhook_key = self.webhook
        self.gateway.flush_recordset()
        self.assertTrue(self.gateway.can_set_webhook)
        with patch("telegram.Bot", getMyBot()):
            self.gateway.set_webhook()
        with patch.object(telegram, "Bot", getMyBot()):
            self.set_message(self.message_02, self.webhook)

        channel = self.env["mail.channel"].search(
            [("gateway_id", "=", self.gateway.id)]
        )
        channel_info = channel.channel_info()[0]
        self.assertEqual(channel_info["gateway"]["id"], self.gateway.id)
        self.assertTrue(channel.avatar_128)

    def test_message_update(self):
        self.gateway.webhook_key = self.webhook
        self.gateway.flush_recordset()
        self.assertTrue(self.gateway.can_set_webhook)
        with patch.object(telegram, "Bot", getMyBot()):
            self.gateway.set_webhook()
        self.assertFalse(
            self.env["mail.channel"].search([("gateway_id", "=", self.gateway.id)])
        )
        with patch.object(telegram, "Bot", getMyBot()):
            self.set_message(self.message_02, self.webhook)
        channel = self.env["mail.channel"].search(
            [("gateway_id", "=", self.gateway.id)]
        )
        self.assertFalse(
            self.env["mail.notification"].search(
                [("gateway_channel_id", "=", channel.id)]
            )
        )
        with patch.object(telegram, "Bot", getMyBot()):
            message = channel.message_post(
                body="HELLO",
                subtype_xmlid="mail.mt_comment",
                message_type="comment",
            )
        with patch.object(telegram, "Bot", getMyBot()):
            channel._message_update_content(message, "New message")
        self.assertRegex(message.body, ".*New message.*")

    def test_messaging(self):
        self.gateway.webhook_key = self.webhook
        self.gateway.flush_recordset()
        self.assertTrue(self.gateway.can_set_webhook)
        with patch.object(telegram, "Bot", getMyBot()):
            self.gateway.set_webhook()
        self.assertFalse(
            self.env["mail.channel"].search([("gateway_id", "=", self.gateway.id)])
        )
        with patch.object(telegram, "Bot", getMyBot()):
            self.set_message(self.message_02, self.webhook)
        messaging = self.env.user._init_messaging()
        self.assertTrue(messaging["gateways"])
        self.assertEqual(1, len(messaging["gateways"]))
        self.assertEqual(self.gateway.id, messaging["gateways"][0]["id"])
        self.assertTrue("gateway_channels" in messaging["current_partner"])
        self.assertEqual(0, len(messaging["current_partner"]["gateway_channels"]))
        channel_info = self.partner.mail_partner_format()
        self.assertTrue("gateway_channels" in channel_info[self.partner])
        self.assertEqual(0, len(channel_info[self.partner]["gateway_channels"]))
        # Assign the partner to the channel
        self.env["mail.guest.manage"].create(
            {
                "partner_id": self.partner.id,
                "guest_id": self.env["mail.guest"]
                .search(
                    [
                        ("gateway_token", "=", self.gateway_token),
                        ("gateway_id", "=", self.gateway.id),
                    ]
                )
                .id,
            }
        ).merge_partner()
        self.assertTrue(self.partner.gateway_channel_ids)
        channel_info = self.partner.mail_partner_format()
        self.assertTrue(channel_info[self.partner]["gateway_channels"])
        self.assertEqual(1, len(channel_info[self.partner]["gateway_channels"]))
