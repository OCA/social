# Copyright 2026 Binhex
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import json

from odoo.tests import tagged

from .common import CLIENT_ADDRESS, UNKNOWN_ADDRESS, MailMessageImportCase


@tagged("post_install", "-at_install")
class TestDashboard(MailMessageImportCase):
    """The panel: a card per receiving channel with what is left to review."""

    def _card(self):
        self.channel.invalidate_recordset()
        return self.channel

    def test_card_counts_what_waits(self):
        self._receive("Hola", sender=UNKNOWN_ADDRESS)
        self._receive("Te paso el pedido")
        card = self._card()
        self.assertEqual(card.message_count, 2)
        self.assertEqual(card.unidentified_count, 1)
        self.assertEqual(card.waiting_count, 1)
        self.assertEqual(card.error_count, 0)
        self.assertEqual(card.open_incident_count, 0)
        self.assertTrue(card.last_message_date)
        other = self.env["mail.message.import.channel"].create(
            {"name": "Other channel", "channel_type": False}
        )
        cards = card | other
        cards.invalidate_recordset()
        self.assertEqual(cards.mapped("message_count"), [2, 0])
        self.assertFalse(other.last_message_date)

    def test_links_open_the_records_of_the_channel(self):
        message = self._receive("Hola", sender=UNKNOWN_ADDRESS)
        action = self.channel.action_view_unidentified()
        self.assertEqual(
            self.env["mail.message.import.message"].search(action["domain"]), message
        )
        conversation = self._receive("Te paso el pedido").conversation_id
        action = self.channel.action_view_waiting()
        self.assertEqual(action["context"], {"search_default_waiting": 1})
        self.assertIn(
            conversation,
            self.env["mail.message.import.conversation"].search(action["domain"]),
        )
        for action in (
            self.channel.action_view_messages(),
            self.channel.action_view_conversations(),
            self.channel.action_view_errors(),
            self.channel.action_view_incidents(),
        ):
            self.assertIn(("channel_id", "in", self.channel.ids), action["domain"])

    def test_graph_shows_a_sample_until_a_message_arrives(self):
        graph = json.loads(self._card().dashboard_graph)[0]
        self.assertTrue(graph["is_sample_data"])
        self.assertEqual(len(graph["values"]), 7)
        self.assertTrue(all(value["value"] for value in graph["values"]))
        self._receive("Hola")
        graph = json.loads(self._card().dashboard_graph)[0]
        self.assertFalse(graph["is_sample_data"])
        self.assertEqual(graph["values"][-1]["value"], 1)

    def test_origin_tells_the_channel_and_the_address(self):
        message = self._receive("Te paso el pedido")
        # The test channel has no type: its name stands for it.
        expected = f"Test channel · {CLIENT_ADDRESS} (Buyer)"
        self.assertEqual(message.origin_display, expected)
        self.assertEqual(message.conversation_id.origin_display, expected)
        self.assertEqual(
            message.authorized_address_id.display_name, f"{CLIENT_ADDRESS} (Buyer)"
        )
        unknown = self._receive("Hola", sender=UNKNOWN_ADDRESS)
        self.assertEqual(unknown.origin_display, f"Test channel · {UNKNOWN_ADDRESS}")

    def test_channel_without_type_asks_for_one(self):
        self.assertEqual(self.channel.state, "not_configured")
        self.assertTrue(self.channel.state_message)
        self.channel.active = False
        self.assertEqual(self.channel.state, "disabled")

    def test_sender_counts_and_links(self):
        message = self._receive("Hola")
        self.sender.invalidate_recordset()
        self.assertEqual(self.sender.address_count, 1)
        self.assertEqual(self.sender.message_count, 1)
        self.assertEqual(self.sender.conversation_count, 1)
        self.assertEqual(self.sender.open_incident_count, 0)
        other = self.env["mail.message.import.sender"].create({"name": "Other"})
        senders = self.sender | other
        senders.invalidate_recordset()
        self.assertEqual(senders.mapped("message_count"), [1, 0])
        self.assertEqual(senders.mapped("conversation_count"), [1, 0])
        action = self.sender.action_view_messages()
        self.assertEqual(
            self.env["mail.message.import.message"].search(action["domain"]), message
        )
        action = self.sender.action_view_conversations()
        self.assertEqual(
            self.env["mail.message.import.conversation"].search(action["domain"]),
            message.conversation_id,
        )
        action = self.sender.action_view_incidents()
        self.assertEqual(action["context"], {"search_default_open": 1})
        self.assertIn(("sender_id", "in", self.sender.ids), action["domain"])

    def test_message_links(self):
        message = self._receive(
            files=[
                {"name": "p.pdf", "raw": b"%PDF-1.4 x", "mimetype": "application/pdf"}
            ]
        )
        self.assertEqual(message.name, "Ana - Document")
        self.assertEqual(message.attachment_count, 1)
        action = message.action_view_attachments()
        self.assertEqual(
            self.env["ir.attachment"].search(action["domain"]), message.attachment_ids
        )
        action = message.action_view_conversation()
        self.assertEqual(action["res_id"], message.conversation_id.id)
        action = message.action_assign_sender()
        self.assertEqual(action["context"], {"default_message_ids": message.ids})
