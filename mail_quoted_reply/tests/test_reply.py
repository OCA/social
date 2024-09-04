# Copyright 2021 Creu Blanca
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import re

from odoo.tests import TransactionCase


class TestMessageReply(TransactionCase):
    def test_reply(self):
        partner = self.env["res.partner"].create({"name": "demo partner"})
        self.assertFalse(
            partner.message_ids.filtered(lambda r: r.message_type != "notification")
        )
        # pylint: disable=C8107
        message = partner.message_post(
            body="demo message",
            message_type="email",
            partner_ids=self.env.ref("base.partner_demo").ids,
        )
        partner.invalidate_recordset()
        self.assertIn(
            message,
            partner.message_ids.filtered(lambda r: r.message_type != "notification"),
        )
        self.assertFalse(
            partner.message_ids.filtered(
                lambda r: r.message_type != "notification" and r != message
            )
        )
        action = message.reply_message()
        wizard = (
            self.env[action["res_model"]].with_context(**action["context"]).create({})
        )
        self.assertTrue(wizard.partner_ids)
        self.assertEqual(message.email_from, wizard.partner_ids.email_formatted)
        # the onchange in the composer isn't triggered in tests, so we check for the
        # correct quote in the context
        email_quote = re.search("<p>.*?</p>", wizard._context["quote_body"]).group()
        self.assertEqual("<p>demo message</p>", email_quote)
        wizard.action_send_mail()
        new_message = partner.message_ids.filtered(
            lambda r: r.message_type != "notification" and r != message
        )
        self.assertTrue(new_message)
        self.assertEqual(1, len(new_message))
