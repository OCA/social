# Copyright 2025 Hunki Enterprises BV
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl-3.0)

from odoo.tests.common import TransactionCase

SUBJECT = "Testsubject 42"
MAIL_WITH_SUBJECT = f"""From: Tester <test@test.com>
To: odoo@test.com
Subject: Re: {SUBJECT}

This is a reply about test subject 42
"""
MAIL_WITH_WRONG_SUBJECT = MAIL_WITH_SUBJECT.replace(
    f"Subject: Re: {SUBJECT}", "Subject: Something entirely else"
)


class TestMailRoutingSubject(TransactionCase):
    def setUp(self):
        super().setUp()
        self.thread = self.env.ref("base.main_partner")
        self.message = self.env["mail.mail"].create(
            {
                "subject": SUBJECT,
                "model": self.thread._name,
                "res_id": self.thread.id,
                "email_to": "test@test.com",
            }
        )

    def test_happy_flow(self):
        """
        Test that the expected flow works
        """
        existing_messages = self.thread.message_ids
        self.env["mail.thread"].message_process(None, MAIL_WITH_SUBJECT)
        new_message = self.thread.message_ids - existing_messages
        self.assertTrue(new_message)

        existing_messages += new_message
        multi_reply = MAIL_WITH_SUBJECT.replace(
            f"Subject: Re: {SUBJECT}", f"Subject: Re: Re:RE: {SUBJECT}"
        )
        self.env["mail.thread"].message_process(None, multi_reply)
        new_message = self.thread.message_ids - existing_messages
        self.assertTrue(new_message)

    def test_failure(self):
        """
        Test various things that can go wrong
        """
        with self.assertRaises(ValueError):
            self.env["mail.thread"].message_process(None, MAIL_WITH_WRONG_SUBJECT)

        self.message.subject = "Testsubject 43"
        with self.assertRaises(ValueError):
            self.env["mail.thread"].message_process(None, MAIL_WITH_SUBJECT)

        self.env.ref("mail_routing_subject.parameter_prefixes").unlink()
        with self.assertRaises(ValueError):
            self.env["mail.thread"].message_process(None, MAIL_WITH_SUBJECT)

    def test_append(self):
        """
        Test that we don't interfere with standard matching
        """
        reply_with_msgid = (
            f"References: {self.message.message_id}\n" + MAIL_WITH_WRONG_SUBJECT
        )
        existing_messages = self.thread.message_ids
        self.env["mail.thread"].message_process(None, reply_with_msgid)
        new_message = self.thread.message_ids - existing_messages
        self.assertTrue(new_message)
