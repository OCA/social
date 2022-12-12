# Copyright 2021 Creu Blanca
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo.tests import TransactionCase


class TestMessageReply(TransactionCase):
    def test_reply(self):
        partner = self.env["res.partner"].create({"name": "demo partner"})
        self.assertFalse(
            partner.message_ids.filtered(lambda r: r.message_type != "notification")
        )
        # pylint: disable=C8107
        message = partner.message_post(body="demo message", message_type="email")
        partner.refresh()
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
            self.env[action["res_model"]].with_context(action["context"]).create({})
        )
        wizard.action_send_mail()
        new_message = partner.message_ids.filtered(
            lambda r: r.message_type != "notification" and r != message
        )
        self.assertTrue(new_message)
        self.assertEqual(1, len(new_message))
