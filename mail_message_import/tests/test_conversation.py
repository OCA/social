# Copyright 2026 Binhex
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from datetime import timedelta
from email.message import EmailMessage
from unittest.mock import patch

from odoo import fields
from odoo.exceptions import UserError
from odoo.tests import tagged
from odoo.tools import mute_logger

from ..services import email_reader
from .common import CLIENT_ADDRESS, MailMessageImportCase

LOGGER = "odoo.addons.mail_message_import.models.mail_message_import_conversation"


@tagged("post_install", "-at_install")
class TestConversation(MailMessageImportCase):
    """The messages of a sender are grouped, queued and processed together."""

    def _patch_processing(self, side_effect):
        Conversation = type(self.env["mail.message.import.conversation"])
        return patch.object(
            Conversation, "_process_messages", autospec=True, side_effect=side_effect
        )

    def test_messages_of_an_address_share_the_conversation(self):
        first = self._receive("Te paso el pedido")
        second = self._receive("Ojo: son 50")
        conversation = first.conversation_id
        self.assertEqual(conversation, second.conversation_id)
        self.assertEqual(conversation.message_count, 2)
        self.assertEqual(conversation.state, "open")
        self.assertTrue(conversation.name.startswith("MSG/"))

    def test_conversation_waits_for_the_inactivity(self):
        conversation = self._receive("Hola").conversation_id
        self.env["mail.message.import.conversation"]._cron_process()
        self.assertEqual(conversation.state, "open")
        expected = fields.Datetime.now() + timedelta(
            minutes=self.config.inactivity_minutes
        )
        self.assertAlmostEqual(
            conversation.process_after, expected, delta=timedelta(seconds=5)
        )

    def test_without_processor_the_conversation_is_finished(self):
        message = self._receive("Hola")
        conversation = message.conversation_id
        self._process()
        self.assertEqual(conversation.state, "done")
        self.assertEqual(message.state, "processed")
        self.assertTrue(conversation.processed_date)
        # A later message opens a new conversation.
        self.assertNotEqual(self._receive("Otro").conversation_id, conversation)

    def test_processor_gets_the_messages_in_order(self):
        first = self._receive("Primero", message_date=fields.Datetime.now())
        second = self._receive(
            "Segundo", message_date=fields.Datetime.now() - timedelta(minutes=1)
        )
        received = []

        def process(conversation, messages):
            received.append(messages)
            conversation._finish(messages)

        with self._patch_processing(process):
            self._process()
        self.assertEqual(received[0].ids, (second | first).ids)

    def test_process_now_does_not_wait_for_the_inactivity(self):
        conversation = self._receive("Hola").conversation_id
        conversation.action_process_now()
        self.assertTrue(conversation.process_requested)
        self.assertLess(
            conversation.process_after,
            fields.Datetime.now() + timedelta(minutes=1),
        )
        self._receive("Y esto")
        self.assertLess(
            conversation.process_after,
            fields.Datetime.now() + timedelta(minutes=1),
            "Only the files on their way are awaited",
        )

    def test_inactive_sender_cancels_the_conversation(self):
        message = self._receive("Hola")
        self.sender.active = False
        self._process()
        self.assertEqual(message.conversation_id.state, "cancelled")
        self.assertEqual(message.state, "ignored")

    def test_failures_are_retried_then_reported(self):
        self.config.max_attempts = 2
        conversation = self._receive("Hola").conversation_id
        with (
            self._patch_processing(RuntimeError("boom")),
            mute_logger(LOGGER),
        ):
            self._process()
            self.assertEqual(conversation.state, "error")
            self.assertTrue(conversation.next_attempt_date, "Retried later")
            self.assertFalse(conversation.incident_ids)
            self._process()
        self.assertEqual(conversation.attempt_count, 2)
        self.assertFalse(conversation.next_attempt_date)
        incident = conversation.incident_ids
        self.assertEqual(incident.incident_type, "processing_error")
        self.assertEqual(incident.category, "technical")
        self.assertIn("boom", incident.description)
        self.assertTrue(incident.can_retry)
        # Retried once the cause is solved.
        incident.action_retry()
        self.assertEqual(incident.state, "resolved")
        self._process()
        self.assertEqual(conversation.state, "done")

    def test_files_left_in_an_unknown_channel_cannot_be_downloaded(self):
        message = self._receive("Hola", media_pending=True)
        conversation = message.conversation_id
        self._process()
        self.assertEqual(conversation.state, "error")
        self.assertFalse(conversation.next_attempt_date, "Retrying would not help")
        self.assertEqual(conversation.open_incident_count, 1)

    def test_forwarded_emails_are_unpacked(self):
        email = EmailMessage()
        email["From"] = "vendor@example.com"
        email["To"] = "buyer@example.com"
        email["Subject"] = "Quote"
        email.set_content("The quote is attached.")
        email.add_attachment(
            b"%PDF-1.4 " + b"1" * 30000,
            maintype="application",
            subtype="pdf",
            filename="quote.pdf",
        )
        message = self._receive(
            "Mira esto",
            files=[
                {
                    "name": "FW quote.eml",
                    "raw": email.as_bytes(),
                    "mimetype": "message/rfc822",
                }
            ],
        )
        self._process()
        self.assertEqual(
            sorted(message.attachment_ids.mapped("name")),
            ["FW quote.eml", "FW quote.eml / quote.pdf"],
        )
        # Not unpacked twice when the conversation is processed again.
        message.conversation_id._unpack_emails(message)
        self.assertEqual(len(message.attachment_ids), 2)

    def test_unreadable_forwarded_email_is_left_as_it_is(self):
        message = self._receive(
            files=[
                {
                    "name": "FW order.msg",
                    "raw": email_reader.OLE_SIGNATURE + b"\x00" * 100,
                    "mimetype": email_reader.MSG,
                }
            ]
        )
        with patch.object(email_reader, "extract_msg", None):
            self._process()
        self.assertEqual(message.conversation_id.state, "done")
        self.assertEqual(message.attachment_ids.mapped("name"), ["FW order.msg"])

    def test_interrupted_processing_is_retried(self):
        self.config.max_attempts = 3
        conversation = self._receive("Hola").conversation_id
        conversation.write(
            {
                "state": "processing",
                "processing_start": fields.Datetime.now() - timedelta(hours=1),
                "attempt_count": 1,
            }
        )
        with mute_logger(LOGGER):
            self.env["mail.message.import.conversation"]._recover_stale()
        self.assertEqual(conversation.state, "error")
        self.assertEqual(conversation.last_error, "The processing was interrupted.")
        self.assertTrue(conversation.next_attempt_date)
        self._process()
        self.assertEqual(conversation.state, "done")

    def test_conversation_created_by_hand_is_numbered(self):
        conversation = self.env["mail.message.import.conversation"].create(
            {
                "channel_id": self.channel.id,
                "company_id": self.company.id,
                "sender_id": self.sender.id,
                "sender_address": CLIENT_ADDRESS,
            }
        )
        self.assertTrue(conversation.name.startswith("MSG/"))

    def test_incident_is_closed_reopened_or_retried(self):
        self.config.max_attempts = 1
        conversation = self._receive("Hola").conversation_id
        with self._patch_processing(RuntimeError("boom")), mute_logger(LOGGER):
            self._process()
        incident = conversation.incident_ids
        action = conversation.action_view_incidents()
        self.assertEqual(
            self.env["mail.message.import.incident"].search(action["domain"]), incident
        )
        self.assertEqual(incident.action_open_conversation()["res_id"], conversation.id)
        incident.activity_schedule("mail.mail_activity_data_todo")
        incident.action_dismiss()
        self.assertEqual(incident.state, "dismissed")
        self.assertEqual(incident.resolved_by_id, self.env.user)
        self.assertFalse(incident.activity_ids, "Nothing is left to do")
        with self.assertRaises(UserError):
            incident.action_retry()
        incident.action_reopen()
        self.assertEqual(incident.state, "open")
        self.assertFalse(incident.resolved_date)
        incident.action_resolve()
        self.assertEqual(incident.state, "resolved")
        self.assertEqual(conversation.action_view_incidents()["context"], {})
