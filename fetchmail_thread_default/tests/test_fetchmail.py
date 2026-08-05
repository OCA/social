# Copyright 2017 Tecnativa - Jairo Llopis <jairo.llopis@tecnativa.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from email.message import EmailMessage
from email.policy import SMTP

from odoo.tests.common import TransactionCase
from odoo.tools import mute_logger


class FetchmailCase(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Incoming mail is processed with administrative rights by fetchmail.
        cls.MailThread = cls.env["mail.thread"].sudo()
        cls.server = cls.env["fetchmail.server"].create(
            {"name": "Default thread test server", "server_type": "local"}
        )
        cls.sink = cls.env["discuss.channel"].create({"name": "Fallback thread"})
        cls.sender = cls.env["res.partner"].create(
            {"name": "Incoming sender", "email": "sender@example.com"}
        )
        cls.server.default_thread_id = cls.sink

    @staticmethod
    def _raw_email(subject, message_id, references=None):
        message = EmailMessage(policy=SMTP)
        message["From"] = "Sender <sender@example.com>"
        message["To"] = "inbox@example.com"
        message["Subject"] = subject
        message["Message-Id"] = message_id
        if references:
            message["References"] = references
            message["In-Reply-To"] = references
        message.set_content("Incoming message body")
        return message.as_bytes()

    def test_available_models(self):
        """Only concrete models supporting chatter appear."""
        available_models = dict(self.server._get_thread_models())
        self.assertIn("discuss.channel", available_models)
        self.assertNotIn("mail.message", available_models)
        for model_name in available_models:
            self.assertTrue(self.env[model_name]._auto)
            self.assertTrue(hasattr(self.env[model_name], "message_post"))

    def test_emptying_default_thread(self):
        """Choosing an ``object_id`` empties ``default_thread_id``."""
        self.server.object_id = self.env["ir.model"]._get("discuss.channel")
        self.server.onchange_server_type()
        self.assertFalse(self.server.default_thread_id)

    def test_emptying_object(self):
        """Choosing a ``default_thread_id`` empties ``object_id``."""
        self.server.object_id = self.env["ir.model"]._get("discuss.channel")
        self.server.default_thread_id = self.sink
        self.server._onchange_remove_object_id()
        self.assertFalse(self.server.object_id)

    @mute_logger("odoo.addons.mail.models.mail_thread", "odoo.models")
    def test_unbound_incoming_email(self):
        """An unbound incoming email gets posted to the sink."""
        subject = "Post this message on the configured fallback thread"
        followers_before = self.sink.message_partner_ids
        result = self.MailThread.with_context(
            default_fetchmail_server_id=self.server.id
        ).message_process(
            model=False,
            message=self._raw_email(
                subject, "<fetchmail-thread-default-unbound@example.com>"
            ),
            save_original=self.server.original,
            strip_attachments=not self.server.attach,
        )
        self.assertEqual(self.server.default_thread_id, self.sink)
        self.assertEqual(result, self.sink.id)
        self.assertEqual(self.sink.message_partner_ids, followers_before)
        self.assertNotIn(self.sender, self.sink.message_partner_ids)
        incoming_message = self.env["mail.message"].search(
            [
                ("model", "=", self.sink._name),
                ("res_id", "=", self.sink.id),
                ("subject", "=", subject),
            ]
        )
        self.assertEqual(len(incoming_message), 1)

    @mute_logger("odoo.addons.mail.models.mail_thread", "odoo.models")
    def test_normal_reply_routing_wins_over_default_thread(self):
        """A reply reference is routed normally instead of to the fallback."""
        target = self.env["discuss.channel"].create({"name": "Normal route target"})
        parent = target.message_post(body="Original message")
        result = self.MailThread.with_context(
            default_fetchmail_server_id=self.server.id
        ).message_process(
            model=False,
            message=self._raw_email(
                "Reply routed normally",
                "<fetchmail-thread-default-reply@example.com>",
                references=parent.message_id,
            ),
        )

        self.assertEqual(result, target.id)
        self.assertFalse(
            self.env["mail.message"].search_count(
                [
                    ("model", "=", self.sink._name),
                    ("res_id", "=", self.sink.id),
                    ("subject", "=", "Reply routed normally"),
                ]
            )
        )
