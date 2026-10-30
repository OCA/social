# Copyright 2026 Binhex
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import itertools
from datetime import timedelta

from odoo import fields
from odoo.tests.common import TransactionCase

CLIENT_ADDRESS = "+34600111222"
UNKNOWN_ADDRESS = "+34699000111"
MESSAGE_UIDS = itertools.count(1)


class MailMessageImportCase(TransactionCase):
    """Data and helpers shared by the tests, whatever the channel: the
    messages are handed over as a channel module does."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(
            context=dict(
                cls.env.context, tracking_disable=True, mail_notrack=True, lang="en_US"
            )
        )
        cls.company = cls.env.company
        # A channel of no type: the tests do not depend on a channel module.
        cls.channel = cls.env["mail.message.import.channel"].create(
            {"name": "Test channel", "channel_type": False}
        )
        cls.sender = cls.env["mail.message.import.sender"].create(
            {"name": "Acme Client"}
        )
        cls.env["mail.message.import.address"].create(
            {
                "sender_id": cls.sender.id,
                "channel_type": cls.channel.channel_type,
                "address": CLIENT_ADDRESS,
                "name": "Buyer",
            }
        )
        cls.config = cls.env["mail.message.import.config"]._get_for_company(cls.company)

    def _receive(self, text=None, sender=CLIENT_ADDRESS, files=None, **values):
        """Receive a message on the test channel, as a channel hands it over.

        :param files: the files of the message, dicts with ``name``, ``raw``
            and ``mimetype``.
        """
        return self.env["mail.message.import.message"]._receive_message(
            self.channel,
            {
                "message_uid": f"test:{next(MESSAGE_UIDS)}",
                "sender_address": sender,
                "sender_name": "Ana",
                "message_type": "document" if files else "text",
                "body": text or False,
                "message_date": fields.Datetime.now(),
                **values,
            },
            files=files,
        )

    def _process(self):
        """Let the inactivity delay pass and run the cron."""
        Conversation = self.env["mail.message.import.conversation"]
        Conversation.search([("state", "=", "open")]).write(
            {"process_after": fields.Datetime.now() - timedelta(seconds=1)}
        )
        Conversation.search(
            [("state", "=", "error"), ("next_attempt_date", "!=", False)]
        ).write({"next_attempt_date": fields.Datetime.now() - timedelta(seconds=1)})
        Conversation._cron_process()
