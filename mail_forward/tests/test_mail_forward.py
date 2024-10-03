# Copyright 2024 Tecnativa - Carlos Lopez
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo.tests import Form, RecordCapturer, tagged
from odoo.tests.common import HttpCase

from odoo.addons.mail.tests.test_mail_composer import TestMailComposer


@tagged("post_install", "-at_install")
class TestMailForward(TestMailComposer, HttpCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner_follower1 = cls.env["res.partner"].create(
            {"name": "Follower1", "email": "follower1@example.com"}
        )
        cls.partner_follower2 = cls.env["res.partner"].create(
            {"name": "Follower2", "email": "follower2@example.com"}
        )
        cls.partner_forward = cls.env["res.partner"].create(
            {"name": "Forward", "email": "forward@example.com"}
        )

    def test_01_mail_forward(self):
        """
        Send an email to followers
        and forward it to another partner.
        """
        ctx = {
            "default_model": self.test_record._name,
            "default_res_id": self.test_record.id,
        }
        composer_form = Form(self.env["mail.compose.message"].with_context(**ctx))
        composer_form.body = "<p>Hello</p>"
        composer_form.partner_ids.add(self.partner_follower1)
        composer_form.partner_ids.add(self.partner_follower2)
        composer = composer_form.save()
        with self.mock_mail_gateway():
            composer._action_send_mail()
        # Verify recipients of mail.message
        message = self.test_record.message_ids[0]
        self.assertEqual(len(message.partner_ids), 2)
        self.assertIn(self.partner_follower1, message.partner_ids)
        self.assertIn(self.partner_follower2, message.partner_ids)
        self.assertNotIn(self.partner_forward, message.partner_ids)
        self.assertNotIn("---------- Forwarded message ---------", message.body)
        # Forward the email
        # only the partner_forward should receive the email
        action_forward = message.action_wizard_forward()
        Message = self.env["mail.compose.message"].with_context(
            **action_forward["context"]
        )
        composer_form = Form(Message, view=action_forward["views"][0][0])
        composer_form.partner_ids.add(self.partner_forward)
        composer = composer_form.save()
        message_domain = [
            ("model", "=", self.test_record._name),
            ("res_id", "=", self.test_record.id),
        ]
        with RecordCapturer(self.env["mail.message"], message_domain) as capture:
            with self.mock_mail_gateway():
                composer._action_send_mail()
        # Verify recipients of mail.message
        forward_message = capture.records
        self.assertEqual(len(forward_message.partner_ids), 1)
        self.assertNotIn(self.partner_follower1, forward_message.partner_ids)
        self.assertIn(self.partner_forward, forward_message.partner_ids)
        self.assertIn("---------- Forwarded message ---------", forward_message.body)

    def test_02_mail_forward_tour(self):
        self.start_tour("/web", "mail_forward.mail_forward_tour", login="admin")

    def test_03_mail_note_not_forward_tour(self):
        self.start_tour(
            "/web", "mail_forward.mail_note_not_forward_tour", login="admin"
        )
