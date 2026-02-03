from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase


class TestConversation(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.stage_new = cls.env.ref("customer_engagement.stage_new")
        cls.stage_open = cls.env.ref("customer_engagement.stage_open")
        cls.stage_pending = cls.env.ref("customer_engagement.stage_pending")
        cls.stage_resolved = cls.env.ref("customer_engagement.stage_resolved")
        cls.stage_closed = cls.env.ref("customer_engagement.stage_closed")

    def test_create_conversation(self):
        """Test conversation creation with default stage."""
        conv = self.env["support.conversation"].create(
            {
                "channel_type": "whatsapp",
                "subject": "Test conversation",
            }
        )
        self.assertEqual(conv.stage_id.code, "new")
        self.assertFalse(conv.closed)
        self.assertTrue(conv.uuid)
        self.assertEqual(len(conv.uuid), 36)  # UUID format

    def test_display_name_with_subject(self):
        """Test display name computation with subject."""
        conv = self.env["support.conversation"].create(
            {
                "channel_type": "email",
                "subject": "Help needed",
            }
        )
        self.assertIn("Help needed", conv.display_name)
        self.assertIn(conv.uuid[:8], conv.display_name)

    def test_display_name_with_partner(self):
        """Test display name computation with partner."""
        partner = self.env["res.partner"].create({"name": "John Doe"})
        conv = self.env["support.conversation"].create(
            {
                "channel_type": "email",
                "partner_id": partner.id,
            }
        )
        self.assertIn("John Doe", conv.display_name)

    def test_display_name_without_subject_or_partner(self):
        """Test display name computation without subject or partner."""
        conv = self.env["support.conversation"].create(
            {
                "channel_type": "whatsapp",
            }
        )
        self.assertEqual(conv.display_name, f"[{conv.uuid[:8]}]")

    def test_valid_transition_new_to_open(self):
        """Test valid transition from new to open."""
        conv = self.env["support.conversation"].create(
            {
                "channel_type": "email",
            }
        )
        conv.write({"stage_id": self.stage_open.id})
        self.assertEqual(conv.stage_id.code, "open")

    def test_valid_transition_open_to_pending(self):
        """Test valid transition from open to pending."""
        conv = self.env["support.conversation"].create(
            {
                "channel_type": "email",
            }
        )
        conv.action_open()
        conv.write({"stage_id": self.stage_pending.id})
        self.assertEqual(conv.stage_id.code, "pending")

    def test_valid_transition_open_to_resolved(self):
        """Test valid transition from open to resolved."""
        conv = self.env["support.conversation"].create(
            {
                "channel_type": "email",
            }
        )
        conv.action_open()
        conv.action_resolve()
        self.assertEqual(conv.stage_id.code, "resolved")

    def test_valid_transition_pending_to_open(self):
        """Test valid transition from pending back to open."""
        conv = self.env["support.conversation"].create(
            {
                "channel_type": "email",
            }
        )
        conv.action_open()
        conv.action_pending()
        conv.action_open()
        self.assertEqual(conv.stage_id.code, "open")

    def test_valid_transition_resolved_to_closed(self):
        """Test valid transition from resolved to closed."""
        conv = self.env["support.conversation"].create(
            {
                "channel_type": "email",
            }
        )
        conv.action_open()
        conv.action_resolve()
        conv.action_close()
        self.assertEqual(conv.stage_id.code, "closed")
        self.assertTrue(conv.closed)

    def test_valid_transition_closed_to_open_reopen(self):
        """Test valid transition from closed to open (reopen)."""
        conv = self.env["support.conversation"].create(
            {
                "channel_type": "email",
            }
        )
        conv.action_open()
        conv.action_resolve()
        conv.action_close()
        conv.action_open()
        self.assertEqual(conv.stage_id.code, "open")
        self.assertFalse(conv.closed)

    def test_invalid_transition_new_to_closed(self):
        """Test invalid transition from new to closed."""
        conv = self.env["support.conversation"].create(
            {
                "channel_type": "email",
            }
        )
        with self.assertRaises(UserError):
            conv.write({"stage_id": self.stage_closed.id})

    def test_invalid_transition_new_to_pending(self):
        """Test invalid transition from new to pending."""
        conv = self.env["support.conversation"].create(
            {
                "channel_type": "email",
            }
        )
        with self.assertRaises(UserError):
            conv.write({"stage_id": self.stage_pending.id})

    def test_invalid_transition_new_to_resolved(self):
        """Test invalid transition from new to resolved."""
        conv = self.env["support.conversation"].create(
            {
                "channel_type": "email",
            }
        )
        with self.assertRaises(UserError):
            conv.write({"stage_id": self.stage_resolved.id})

    def test_invalid_transition_open_to_closed(self):
        """Test invalid transition from open to closed (must resolve first)."""
        conv = self.env["support.conversation"].create(
            {
                "channel_type": "email",
            }
        )
        conv.action_open()
        with self.assertRaises(UserError):
            conv.write({"stage_id": self.stage_closed.id})

    def test_transition_history(self):
        """Test that transitions are recorded in history."""
        conv = self.env["support.conversation"].create(
            {
                "channel_type": "whatsapp",
            }
        )
        conv.action_open()
        history = self.env["support.conversation.history"].search(
            [("conversation_id", "=", conv.id)]
        )
        self.assertEqual(len(history), 1)
        self.assertEqual(history.to_stage_id.code, "open")
        self.assertEqual(history.from_stage_id.code, "new")

    def test_multiple_transitions_history(self):
        """Test multiple transitions are recorded in history."""
        conv = self.env["support.conversation"].create(
            {
                "channel_type": "email",
            }
        )
        conv.action_open()
        conv.action_resolve()
        conv.action_close()

        history = self.env["support.conversation.history"].search(
            [("conversation_id", "=", conv.id)], order="create_date asc"
        )

        self.assertEqual(len(history), 3)
        self.assertEqual(history[0].to_stage_id.code, "open")
        self.assertEqual(history[1].to_stage_id.code, "resolved")
        self.assertEqual(history[2].to_stage_id.code, "closed")

    def test_first_response_timestamp(self):
        """Test first_response_at is set on first open."""
        conv = self.env["support.conversation"].create(
            {
                "channel_type": "email",
            }
        )
        self.assertFalse(conv.first_response_at)
        conv.action_open()
        self.assertTrue(conv.first_response_at)

    def test_first_response_timestamp_not_updated_on_reopen(self):
        """Test first_response_at is not updated on reopen."""
        conv = self.env["support.conversation"].create(
            {
                "channel_type": "email",
            }
        )
        conv.action_open()
        first_response = conv.first_response_at
        conv.action_resolve()
        conv.action_open()
        self.assertEqual(conv.first_response_at, first_response)

    def test_resolved_timestamp(self):
        """Test resolved_at is set on resolve."""
        conv = self.env["support.conversation"].create(
            {
                "channel_type": "email",
            }
        )
        conv.action_open()
        self.assertFalse(conv.resolved_at)
        conv.action_resolve()
        self.assertTrue(conv.resolved_at)

    def test_resolved_timestamp_cleared_on_reopen(self):
        """Test resolved_at is cleared on reopen."""
        conv = self.env["support.conversation"].create(
            {
                "channel_type": "email",
            }
        )
        conv.action_open()
        conv.action_resolve()
        self.assertTrue(conv.resolved_at)
        conv.action_open()
        self.assertFalse(conv.resolved_at)

    def test_channel_types(self):
        """Test all channel types can be created."""
        channel_types = [
            "email",
            "whatsapp",
            "instagram",
            "messenger",
            "telegram",
            "livechat",
            "api",
        ]
        for channel in channel_types:
            conv = self.env["support.conversation"].create(
                {
                    "channel_type": channel,
                }
            )
            self.assertEqual(conv.channel_type, channel)

    def test_priority_levels(self):
        """Test all priority levels."""
        for priority in ["0", "1", "2", "3"]:
            conv = self.env["support.conversation"].create(
                {
                    "channel_type": "email",
                    "priority": priority,
                }
            )
            self.assertEqual(conv.priority, priority)

    def test_default_priority(self):
        """Test default priority is Normal (1)."""
        conv = self.env["support.conversation"].create(
            {
                "channel_type": "email",
            }
        )
        self.assertEqual(conv.priority, "1")

    def test_same_stage_transition_allowed(self):
        """Test that transitioning to the same stage is allowed."""
        conv = self.env["support.conversation"].create(
            {
                "channel_type": "email",
            }
        )
        conv.action_open()
        # This should not raise an error
        conv.write({"stage_id": self.stage_open.id})
        self.assertEqual(conv.stage_id.code, "open")


class TestConversationStage(TransactionCase):
    def test_stage_sequence(self):
        """Test that stages have correct sequence ordering."""
        stages = self.env["support.conversation.stage"].search([], order="sequence")
        codes = [s.code for s in stages]
        self.assertEqual(codes, ["new", "open", "pending", "resolved", "closed"])

    def test_stage_closed_flag(self):
        """Test that only 'closed' stage has closed=True."""
        closed_stages = self.env["support.conversation.stage"].search(
            [("closed", "=", True)]
        )
        self.assertEqual(len(closed_stages), 1)
        self.assertEqual(closed_stages.code, "closed")


class TestConversationHistory(TransactionCase):
    def test_history_creation(self):
        """Test history record creation."""
        conv = self.env["support.conversation"].create(
            {
                "channel_type": "email",
            }
        )
        stage_open = self.env.ref("customer_engagement.stage_open")

        history = self.env["support.conversation.history"].create(
            {
                "conversation_id": conv.id,
                "from_stage_id": conv.stage_id.id,
                "to_stage_id": stage_open.id,
            }
        )

        self.assertEqual(history.conversation_id, conv)
        self.assertEqual(history.to_stage_id, stage_open)
        self.assertTrue(history.user_id)

    def test_history_cascade_delete(self):
        """Test history is deleted when conversation is deleted."""
        conv = self.env["support.conversation"].create(
            {
                "channel_type": "email",
            }
        )
        conv.action_open()

        history_count = self.env["support.conversation.history"].search_count(
            [("conversation_id", "=", conv.id)]
        )
        self.assertGreater(history_count, 0)

        conv_id = conv.id
        conv.unlink()

        history_count = self.env["support.conversation.history"].search_count(
            [("conversation_id", "=", conv_id)]
        )
        self.assertEqual(history_count, 0)
