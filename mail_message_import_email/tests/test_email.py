# Copyright 2026 Binhex
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import email
from email.message import EmailMessage
from email.utils import make_msgid
from unittest.mock import patch

from odoo.exceptions import ValidationError
from odoo.tests import Form, tagged

from odoo.addons.mail_message_import.tests.common import MailMessageImportCase

RECEIVING = "orders@example.com"
ADDRESS = "ana@acme.example"
UNKNOWN = "someone@elsewhere.example"
PDF = b"%PDF-1.4\n" + b"1" * 30000
LOGO = b"\x89PNG\r\n\x1a\n" + b"1" * 2000
PHOTO = b"\xff\xd8\xff\xe0" + b"1" * 30000
MESSAGE_MODEL = "mail.message.import.message"


@tagged("post_install", "-at_install")
class TestEmail(MailMessageImportCase):
    """The emails read by the incoming server of a receiving channel are
    received messages, identified and grouped as those of every channel."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.email_channel = cls.env["mail.message.import.channel"].create(
            {"name": "Orders", "channel_type": "email", "email_address": RECEIVING}
        )
        cls.address = cls.env["mail.message.import.address"].create(
            {
                "sender_id": cls.sender.id,
                "channel_type": "email",
                "address": "Ana <Ana@Acme.example>",
            }
        )

    def _email(
        self,
        sender=f"Ana <{ADDRESS}>",
        subject="Weekly order",
        body="10 boxes of tomatoes",
        to=RECEIVING,
        files=(),
        in_reply_to=None,
    ):
        message = EmailMessage()
        message["From"] = sender
        message["To"] = to
        message["Subject"] = subject
        message["Message-Id"] = make_msgid(domain="acme.example")
        if in_reply_to:
            message["In-Reply-To"] = in_reply_to
            message["References"] = in_reply_to
        message.set_content(body)
        for name, data, mimetype in files:
            maintype, subtype = mimetype.split("/")
            message.add_attachment(
                data, maintype=maintype, subtype=subtype, filename=name
            )
        return message.as_bytes()

    def _deliver_email(
        self, raw, server=None, save_original=False, model=MESSAGE_MODEL
    ):
        """Hand an email to the mail gateway, as an incoming mail server does."""
        MailThread = self.env["mail.thread"]
        if server:
            MailThread = MailThread.with_context(default_fetchmail_server_id=server.id)
        MailThread.message_process(model, raw, save_original=save_original)
        message_id = email.message_from_bytes(raw)["Message-Id"].strip()
        return self.env[MESSAGE_MODEL].search(
            [("message_uid", "=", f"email:{message_id}")]
        )

    def _server(self):
        return self.env["fetchmail.server"].create(
            {
                "name": "Mailbox of the channel",
                "server_type": "imap",
                "server": "imap.example.com",
                "port": 993,
                "is_ssl": True,
                "user": RECEIVING,
                "password": "secret",
                "object_id": self.env["ir.model"]._get_id(MESSAGE_MODEL),
            }
        )

    def test_authorized_address_identifies_the_sender(self):
        message = self._deliver_email(self._email())
        self.assertEqual(message.message_type, "email")
        self.assertEqual(message.channel_id, self.email_channel)
        self.assertEqual(message.sender_id, self.sender)
        self.assertEqual(message.authorized_address_id, self.address)
        self.assertEqual(message.sender_address, ADDRESS)
        self.assertEqual(message.sender_name, "Ana")
        self.assertEqual(message.email_subject, "Weekly order")
        self.assertEqual(message.name, "Ana - Weekly order")
        self.assertEqual(message.state, "queued")
        self.assertTrue(message.conversation_id)
        self.assertIn("Subject: Weekly order", message.body)
        self.assertIn("10 boxes of tomatoes", message.body)
        # The email stays in the chatter of the message.
        self.assertEqual(message.mail_message_id.model, MESSAGE_MODEL)
        self.assertEqual(message.message_ids, message.mail_message_id)

    def test_files_without_signature_images(self):
        raw = self._email(
            files=[
                ("order.pdf", PDF, "application/pdf"),
                ("logo.png", LOGO, "image/png"),
                ("photo.jpg", PHOTO, "image/jpeg"),
            ]
        )
        message = self._deliver_email(raw, save_original=True)
        self.assertEqual(
            sorted(message.attachment_ids.mapped("name")), ["order.pdf", "photo.jpg"]
        )
        self.assertEqual(
            set(message.attachment_ids.mapped("res_model")), {MESSAGE_MODEL}
        )

    def test_email_is_processed_as_a_message(self):
        message = self._deliver_email(
            self._email(files=[("order.pdf", PDF, "application/pdf")])
        )
        received = []

        def process(conversation, messages):
            received.append(messages)
            conversation._finish(messages)

        Conversation = type(self.env["mail.message.import.conversation"])
        with patch.object(
            Conversation, "_process_messages", autospec=True, side_effect=process
        ):
            self._process()
        self.assertEqual(received[0], message)
        self.assertEqual(received[0].attachment_ids.mapped("name"), ["order.pdf"])
        self.assertEqual(message.state, "processed")

    def test_unknown_address_is_kept_unidentified(self):
        message = self._deliver_email(self._email(sender=UNKNOWN))
        self.assertEqual(message.state, "unidentified")
        self.assertFalse(message.sender_id)
        self.assertFalse(message.conversation_id)

    def test_assign_sender_authorizes_the_address(self):
        message = self._deliver_email(self._email(sender=f"Luis <{UNKNOWN}>"))
        wizard = Form(
            self.env["mail.message.import.assign.sender"].with_context(
                default_message_ids=message.ids
            )
        )
        wizard.sender_id = self.sender
        wizard.save().action_assign()
        self.assertEqual(message.sender_id, self.sender)
        self.assertEqual(message.state, "queued")
        self.assertEqual(message.authorized_address_id.channel_type, "email")
        self.assertEqual(message.authorized_address_id.address_normalized, UNKNOWN)
        self.assertEqual(message.authorized_address_id.name, "Luis")

    def test_same_email_is_received_once(self):
        raw = self._email()
        first = self._deliver_email(raw)
        self.assertEqual(self._deliver_email(raw), first)
        self.assertEqual(len(first.conversation_id.message_ids), 1)

    def test_reply_is_a_new_message(self):
        first = self._deliver_email(self._email())
        reply = self._deliver_email(
            self._email(
                subject="Re: Weekly order",
                body="Better 12 boxes",
                in_reply_to=first.mail_message_id.message_id,
            )
        )
        self.assertTrue(reply)
        self.assertNotEqual(reply, first)
        self.assertEqual(reply.reply_to_uid, first.message_uid)
        self.assertEqual(reply.conversation_id, first.conversation_id)
        self.assertEqual(len(first.message_ids), 1, "Nothing is posted on the first")

    def test_reply_routed_by_odoo_is_a_new_message(self):
        """A reply that reaches Odoo by another way than the incoming server
        of the channel: the mail gateway routes it to the previous message."""
        first = self._deliver_email(self._email())
        reply = self._deliver_email(
            self._email(
                subject="Re: Weekly order",
                to="other@acme.example",
                in_reply_to=first.mail_message_id.message_id,
            ),
            model=False,
        )
        self.assertNotEqual(reply, first)
        self.assertEqual(reply.channel_id, self.email_channel)
        self.assertEqual(len(first.message_ids), 1, "Nothing is posted on the first")

    def test_incoming_server_chooses_the_channel(self):
        server = self._server()
        self.email_channel.fetchmail_server_id = server
        # Redirected by the mailbox: the receiving address is not a recipient.
        message = self._deliver_email(
            self._email(to="other@acme.example"), server=server
        )
        self.assertEqual(message.channel_id, self.email_channel)
        with self.assertRaises(ValueError):
            self._deliver_email(self._email(to="other@acme.example"))

    def test_channel_state(self):
        channel = self.email_channel
        self.assertEqual(channel.state, "not_configured")
        self.assertIn("incoming mail server", channel.state_message)
        server = self._server()
        channel.fetchmail_server_id = server
        self.assertEqual(channel.state, "pending")
        server.state = "done"
        channel.invalidate_recordset(["state"])
        self.assertEqual(channel.state, "connected")
        self.assertFalse(channel.state_message)
        self.assertEqual(channel.action_open_mail_server()["res_id"], server.id)

    def test_channel_requirements(self):
        Channel = self.env["mail.message.import.channel"]
        with self.assertRaises(ValidationError):
            Channel.create({"name": "Without address", "channel_type": "email"})
        with self.assertRaises(ValidationError):
            Channel.create(
                {
                    "name": "Repeated",
                    "channel_type": "email",
                    "email_address": RECEIVING,
                }
            )
        other_server = self._server()
        other_server.object_id = self.env["ir.model"]._get_id("res.partner")
        with self.assertRaises(ValidationError):
            self.email_channel.fetchmail_server_id = other_server

    def test_new_server_is_set_up_for_the_channel(self):
        Server = self.env["fetchmail.server"]
        fields_list = ["server_type", "is_ssl", "port", "object_id", "attach"]
        model = self.env["ir.model"]._get_id(MESSAGE_MODEL)
        defaults = Server.with_context(
            mail_message_import_mail_server=True
        ).default_get(fields_list)
        self.assertEqual(defaults["object_id"], model)
        self.assertEqual(defaults["server_type"], "imap")
        self.assertEqual(defaults["port"], 993)
        self.assertTrue(defaults["is_ssl"])
        self.assertTrue(defaults["attach"])
        self.assertNotEqual(Server.default_get(fields_list).get("object_id"), model)
        defaults = Server.with_context(
            mail_message_import_mail_server=True, default_port=143
        ).default_get(fields_list)
        self.assertEqual(defaults["port"], 143, "The context wins")
        # The button opens it with the address and links it to the channel.
        action = self.email_channel.action_open_mail_server()
        form = Form(Server.with_context(**action["context"]))
        form.server = "imap.example.com"
        form.password = "secret"
        server = form.save()
        self.assertEqual(server.name, "Orders")
        self.assertEqual(server.user, RECEIVING)
        self.assertEqual(server.object_id.model, MESSAGE_MODEL)
        self.assertEqual(self.email_channel.fetchmail_server_id, server)

    def test_address_identifies_a_single_sender(self):
        other = self.env["mail.message.import.sender"].create({"name": "Other"})
        Address = self.env["mail.message.import.address"]
        with self.assertRaises(ValidationError):
            Address.create(
                {
                    "sender_id": other.id,
                    "channel_type": "email",
                    "address": ADDRESS.upper(),
                }
            )
        with self.assertRaises(ValidationError):
            Address.create(
                {
                    "sender_id": other.id,
                    "channel_type": "email",
                    "address": "not an address",
                }
            )

    def test_other_channels_keep_their_chatter_empty(self):
        message = self._receive("Hola")
        self.assertEqual(message.state, "queued")
        self.assertFalse(message.message_ids)
