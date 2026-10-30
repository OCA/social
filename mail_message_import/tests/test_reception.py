# Copyright 2026 Binhex
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo.exceptions import ValidationError
from odoo.tests import Form, tagged

from .common import CLIENT_ADDRESS, UNKNOWN_ADDRESS, MailMessageImportCase


@tagged("post_install", "-at_install")
class TestReception(MailMessageImportCase):
    """The reception common to every channel: what a channel hands over is
    identified, authorized and grouped the same way."""

    def test_authorized_address_identifies_the_sender(self):
        message = self._receive("Hola")
        self.assertEqual(message.sender_id, self.sender)
        self.assertEqual(message.authorized_address_id.address, CLIENT_ADDRESS)
        self.assertEqual(message.state, "queued")
        self.assertEqual(message.conversation_id.sender_address, CLIENT_ADDRESS)
        self.assertEqual(message.company_id, self.sender.company_id)

    def test_files_are_bound_to_the_message(self):
        message = self._receive(
            files=[
                {"name": "p.pdf", "raw": b"%PDF-1.4 x", "mimetype": "application/pdf"}
            ]
        )
        self.assertEqual(message.message_type, "document")
        self.assertEqual(message.attachment_ids.name, "p.pdf")
        self.assertEqual(
            message.attachment_ids.res_model, "mail.message.import.message"
        )
        self.assertEqual(message.attachment_ids.res_id, message.id)

    def test_unknown_address_is_kept_unidentified(self):
        message = self._receive("Hola", sender=UNKNOWN_ADDRESS)
        self.assertEqual(message.state, "unidentified")
        self.assertFalse(message.sender_id)
        self.assertFalse(message.conversation_id)

    def test_a_message_is_received_once(self):
        message = self._receive("Hola")
        self.assertTrue(
            self.env["mail.message.import.message"]._is_known_uid(message.message_uid)
        )
        self.assertFalse(
            self.env["mail.message.import.message"]._is_known_uid("test:x")
        )

    def test_ignored_types(self):
        message = self._receive(message_type="other")
        self.assertEqual(message.state, "ignored")
        self.assertFalse(message.conversation_id)

    def test_assign_unknown_address_to_sender(self):
        messages = self._receive("Hola", sender=UNKNOWN_ADDRESS) | self._receive(
            "Pedido", sender=UNKNOWN_ADDRESS
        )
        wizard = Form(
            self.env["mail.message.import.assign.sender"].with_context(
                default_message_ids=messages.ids
            )
        )
        wizard.sender_id = self.sender
        wizard.save().action_assign()
        self.assertEqual(set(messages.mapped("state")), {"queued"})
        self.assertEqual(len(messages.conversation_id), 1)
        self.assertIn(UNKNOWN_ADDRESS, self.sender.address_ids.mapped("address"))
        self.assertEqual(self._receive("Otro", sender=UNKNOWN_ADDRESS).state, "queued")

    def test_assign_without_processing_ignores_the_messages(self):
        message = self._receive("Hola", sender=UNKNOWN_ADDRESS)
        wizard = self.env["mail.message.import.assign.sender"].create(
            {
                "message_ids": [(6, 0, message.ids)],
                "sender_id": self.sender.id,
                "authorize_address": False,
                "process_messages": False,
            }
        )
        wizard.action_assign()
        self.assertEqual(message.state, "ignored")
        self.assertEqual(message.sender_id, self.sender)
        self.assertNotIn(UNKNOWN_ADDRESS, self.sender.address_ids.mapped("address"))

    def test_address_cannot_identify_two_senders(self):
        other = self.env["mail.message.import.sender"].create({"name": "Other sender"})
        values = {
            "sender_id": other.id,
            "channel_type": self.channel.channel_type,
            "address": CLIENT_ADDRESS,
        }
        with self.assertRaises(ValidationError):
            self.env["mail.message.import.address"].create(values)
        other.company_id = self.env["res.company"].create({"name": "Company B"})
        self.assertTrue(self.env["mail.message.import.address"].create(values))
        with self.assertRaises(ValidationError):
            other.company_id = self.company

    def test_settings_are_checked(self):
        with self.assertRaises(ValidationError):
            self.config.inactivity_minutes = 0
        with self.assertRaises(ValidationError):
            self.config.max_attempts = 0
