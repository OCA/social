# -*- coding: utf-8 -*-
# Copyright 2017 Jairo Llopis <jairo.llopis@tecnativa.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from openerp.addons.mail.tests.test_mail_gateway import MAIL_TEMPLATE
from openerp.tests.common import SavepointCase
from openerp.tools import mute_logger


class FetchmailCase(SavepointCase):
    @classmethod
    def setUpClass(cls):
        super(FetchmailCase, cls).setUpClass()
        cls.server = cls.env.ref("fetchmail_thread_default.demo_server")
        cls.sink = cls.env.ref("fetchmail_thread_default.demo_sink")
        cls.MailThread = cls.env["mail.thread"]

    def test_available_models(self):
        """Non-``mail.thread`` models don't appear."""
        for record in self.server._get_thread_models():
            self.assertNotEqual(record[0], "mail.message")

    def test_emptying_default_thread(self):
        """Choosing an ``object_id`` empties ``default_thread_id``."""
        self.assertEqual(
            self.server.onchange_server_type(object_id=1)
            ["value"]["default_thread_id"],
            False)

    def test_emptying_object(self):
        """Choosing a ``default_thread_id`` empties ``object_id``."""
        self.server.object_id = self.env["ir.model"].search([], limit=1)
        self.server._onchange_remove_object_id()
        self.assertFalse(self.server.object_id)

    @mute_logger('openerp.addons.mail.models.mail_thread', 'openerp.models')
    def test_unbound_incoming_email(self):
        """An unbound incoming email gets posted to the sink."""
        # Imitate what self.server.feth_mail() would do
        result = (
            self.MailThread.with_context(fetchmail_server_id=self.server.id)
            .message_process(
                self.server.object_id.model,
                MAIL_TEMPLATE.format(
                    email_from="spambot@example.com",
                    to="you@example.com",
                    cc="nobody@example.com",
                    subject="I'm a robot, hello",
                    extra="",
                    msg_id="<fitter.happier.more.productive@example.com>",
                ),
                save_original=self.server.original,
                strip_attachments=not self.server.attach,
            )
        )
        self.assertEqual(self.server.default_thread_id, self.sink)
        self.assertEqual(result, self.sink.id)
        # Nobody subscribed
        self.assertFalse(self.sink.message_partner_ids)
        # Message entered channel
        self.assertEqual(self.sink.message_ids.subject, "I'm a robot, hello")
