# Copyright 2026 Binhex
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo.exceptions import ValidationError
from odoo.tests import Form, new_test_user, tagged

from ..models.mail_message_import_address import normalize_phone
from .common import CLIENT_PHONE, MailMessageImportWhatsappCase

UNKNOWN_PHONE = "34699000111"


@tagged("post_install", "-at_install")
class TestReception(MailMessageImportWhatsappCase):
    """The messages posted by the gateway are received messages, identified by
    the phone of their sender."""

    def test_authorized_phone_identifies_the_sender(self):
        message = self._receive("Hola")
        self.assertEqual(message.channel_id, self.whatsapp_channel)
        self.assertEqual(message.sender_id, self.sender)
        self.assertEqual(message.authorized_address_id.address_normalized, CLIENT_PHONE)
        self.assertEqual(message.sender_address, f"+{CLIENT_PHONE}")
        self.assertEqual(message.sender_name, "Ana")
        self.assertEqual(message.body, "Hola")
        self.assertEqual(message.state, "queued")
        self.assertEqual(message.company_id, self.sender.company_id)
        # The gateway still posts it in its chat.
        self.assertEqual(message.discuss_channel_id.gateway_id, self.gateway)
        self.assertEqual(message.mail_message_id.res_id, message.discuss_channel_id.id)
        self.assertIn('"id"', message.raw_payload)

    def test_sender_receives_on_the_numbers_of_its_company(self):
        company_b = self.env["res.company"].create({"name": "Company B"})
        sender_b = self.env["mail.message.import.sender"].create(
            {"name": "Sender B", "company_id": company_b.id}
        )
        self.env["mail.message.import.address"].create(
            {
                "sender_id": sender_b.id,
                "channel_type": "whatsapp",
                "address": "+34611000333",
            }
        )
        message = self._receive("Hola", sender="34611000333")
        self.assertEqual(message.state, "unidentified")
        self.assertEqual(message.company_id, self.company)
        # The number (and its gateway) of the company B.
        self.gateway.company_id = company_b
        self.whatsapp_channel.company_id = company_b
        message = self._receive("Hola", sender="34611000333")
        self.assertEqual(message.sender_id, sender_b)
        self.assertEqual(message.company_id, company_b)

    def test_unknown_phone_is_kept_unidentified(self):
        message = self._receive("Presupuesto", sender=UNKNOWN_PHONE)
        self.assertEqual(message.state, "unidentified")
        self.assertFalse(message.sender_id)
        self.assertFalse(message.conversation_id)

    def test_other_number_is_not_captured(self):
        payload = self._payload(text="Otro número")
        payload["entry"][0]["changes"][0]["value"]["metadata"]["phone_number_id"] = (
            "777"
        )
        self.assertFalse(self._deliver(payload))

    def test_number_of_the_gateway_without_metadata(self):
        payload = self._payload(text="Sin metadatos")
        del payload["entry"][0]["changes"][0]["value"]["metadata"]
        self.assertEqual(self._deliver(payload).channel_id, self.whatsapp_channel)

    def test_reaction_is_ignored(self):
        message = self._receive(
            reaction={"message_id": "wamid.X", "emoji": "x"}, type="reaction"
        )
        self.assertEqual(message.state, "ignored")
        self.assertFalse(message.mail_message_id, "The gateway posts no reaction")
        self.assertFalse(message.conversation_id)

    def test_unknown_type_is_other(self):
        message = self._receive("Nuevo tipo", type="poll")
        self.assertEqual(message.message_type, "other")
        self.assertEqual(message.state, "ignored")

    def test_text_of_every_kind_of_message(self):
        Message = self.env["mail.message.import.message"]
        text = Message._message_text(
            {
                "button": {"text": "Confirmar"},
                "interactive": {
                    "list_reply": {"title": "Tomate", "description": "Caja de 5 kg"}
                },
                "location": {"name": "Almacén", "latitude": 40.4, "longitude": -3.7},
                "contacts": [
                    {
                        "name": {"formatted_name": "Luis"},
                        "phones": [{"phone": "+34 600 000 001"}],
                    }
                ],
            }
        )
        self.assertEqual(
            text.split("\n"),
            [
                "Confirmar",
                "Tomate",
                "Caja de 5 kg",
                "Almacén  40.4 -3.7",
                "Luis +34 600 000 001",
            ],
        )
        self.assertFalse(Message._message_text({}))
        self.assertTrue(Message._message_date({"timestamp": "not a date"}))

    def test_same_wamid_is_processed_once(self):
        payload = self._payload(text="Una vez")
        first = self._deliver(payload)
        second = self._deliver(payload)
        self.assertEqual(first, second)
        self.assertEqual(len(first.conversation_id.message_ids), 1)

    def test_assign_unknown_phone_to_sender(self):
        messages = self._receive("Hola", sender=UNKNOWN_PHONE) | self._receive(
            "Presupuesto", sender=UNKNOWN_PHONE
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
        self.assertIn(
            UNKNOWN_PHONE, self.sender.address_ids.mapped("address_normalized")
        )

    def test_phone_cannot_identify_two_senders(self):
        other = self.env["mail.message.import.sender"].create({"name": "Other sender"})
        values = {
            "sender_id": other.id,
            "channel_type": "whatsapp",
            "address": f"+{CLIENT_PHONE}",
        }
        with self.assertRaises(ValidationError):
            self.env["mail.message.import.address"].create(values)
        # Possible for a sender of another company.
        other.company_id = self.env["res.company"].create({"name": "Company B"})
        self.assertTrue(self.env["mail.message.import.address"].create(values))
        # And forbidden again if both senders are of the same company.
        with self.assertRaises(ValidationError):
            other.company_id = self.company

    def test_phone_normalization(self):
        self.company.country_id = self.env.ref("base.es")
        phone = self.env["mail.message.import.address"].create(
            {
                "sender_id": self.sender.id,
                "channel_type": "whatsapp",
                "address": "699 12 34 56",
            }
        )
        self.assertEqual(phone.address_normalized, "34699123456")
        phone.address = "0034 699 12 34 57"
        self.assertEqual(phone.address_normalized, "34699123457")
        with self.assertRaises(ValidationError):
            phone.address = "12 34"

    def test_document_is_copied_with_its_name(self):
        payload = self._payload(
            type="document",
            document={
                "id": "MEDIA1",
                "filename": "presupuesto.pdf",
                "mime_type": "application/pdf",
                "caption": "El presupuesto",
            },
        )
        with self._media(b"%PDF-1.4 test", "application/pdf"):
            message = self._deliver(payload)
        self.assertEqual(message.message_type, "document")
        self.assertEqual(message.body, "El presupuesto")
        self.assertEqual(message.attachment_ids.name, "presupuesto.pdf")
        self.assertEqual(
            message.attachment_ids.res_model, "mail.message.import.message"
        )
        self.assertEqual(message.attachment_ids.res_id, message.id)
        self.assertEqual(
            message.attachment_ids.checksum,
            message.mail_message_id.attachment_ids.checksum,
        )

    def test_message_is_processed_with_its_files(self):
        with self._media(b"\xff\xd8\xff photo", "image/jpeg"):
            message = self._deliver(
                self._payload(type="image", image={"id": "MEDIA2", "caption": "Foto"})
            )
        self._process()
        self.assertEqual(message.state, "processed")
        self.assertEqual(len(message.attachment_ids), 1)

    # ------------------------------------------------------------------
    # Receiving channel
    # ------------------------------------------------------------------

    def test_whatsapp_channel_needs_its_gateway(self):
        with self.assertRaises(ValidationError):
            self.env["mail.message.import.channel"].create(
                {"name": "Without gateway", "channel_type": "whatsapp"}
            )

    def test_number_of_the_gateway_is_proposed(self):
        form = Form(self.env["mail.message.import.channel"])
        form.name = "Another number"
        form.channel_type = "whatsapp"
        gateway = self.gateway.copy({"token": "other-token", "webhook_key": "other"})
        form.gateway_id = gateway
        self.assertEqual(form.phone_number_id, "1099")
        action = self.whatsapp_channel.action_open_gateway()
        self.assertEqual(action["res_id"], self.gateway.id)

    def test_channel_state(self):
        channel = self.whatsapp_channel
        self.assertEqual(channel.state, "connected")
        self.gateway.integrated_webhook_state = "pending"
        self.assertEqual(channel.state, "pending")
        self.gateway.webhook_secret = False
        self.assertEqual(channel.state, "not_configured")
        self.assertIn("webhook secret", channel.state_message)

    def test_other_channels_and_payloads(self):
        self.assertEqual(normalize_phone("  "), "")
        other = self.env["mail.message.import.channel"].create(
            {"name": "Other channel", "channel_type": False}
        )
        self.assertEqual(other._channel_state()[0], "not_configured")
        address = self.env["mail.message.import.address"].new(
            {"channel_type": False, "address": "x"}
        )
        self.assertIn("not valid", address._invalid_address_message())
        Message = self.env["mail.message.import.message"]
        self.assertFalse(Message._capture_inbound(self.gateway, None, {}, {}, None))
        self.assertFalse(Message._sender_name({"contacts": [{"wa_id": "1"}]}, "2"))

    def test_secrets_are_not_exposed(self):
        manager = new_test_user(
            self.env,
            login="mail_message_import_whatsapp_manager",
            groups="mail_message_import.group_mail_message_import_manager",
        )
        channel = self.whatsapp_channel.with_user(manager)
        self.assertEqual(channel.state, "connected")
        self.assertNotIn("meta-token", str(channel.read(["state_message"])))
