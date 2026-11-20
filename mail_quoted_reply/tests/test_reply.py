# Copyright 2021 Creu Blanca
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import re

from odoo.tests import TransactionCase


class TestMessageReply(TransactionCase):
    def _create_message(self, partner, body, subject=False, email_from=False):
        values = {
            "model": partner._name,
            "res_id": partner.id,
            "body": body,
            "message_type": "email",
        }
        if subject is not False:
            values["subject"] = subject
        if email_from is not False:
            values["email_from"] = email_from
        return self.env["mail.message"].create(values)

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

    def test_reply_context_subject_only_when_original_has_subject(self):
        partner = self.env["res.partner"].create({"name": "demo partner"})
        message = partner.message_post(
            body="demo message",
            subject="My Subject",
            message_type="email",
            partner_ids=self.env.ref("base.partner_demo").ids,
        )
        action = message.reply_message()
        self.assertEqual("Re: My Subject", action["context"].get("default_subject"))

        wizard = (
            self.env[action["res_model"]].with_context(**action["context"]).create({})
        )
        wizard._compute_subject()
        self.assertEqual("Re: My Subject", wizard.subject)

    def test_reply_context_subject_not_set_when_original_has_no_subject(self):
        partner = self.env["res.partner"].create({"name": "demo partner"})
        message = partner.message_post(
            body="demo message",
            message_type="email",
            partner_ids=self.env.ref("base.partner_demo").ids,
        )
        message.subject = False
        action = message.reply_message()
        self.assertFalse(action["context"].get("default_subject"))

    def test_quote_body_is_sanitized_and_contains_signature(self):
        self.env.user.signature = "<p>--sig--</p>"

        partner = self.env["res.partner"].create({"name": "demo partner"})
        message = self._create_message(
            partner,
            body="<p>Hello</p><script>alert(1)</script>",
            subject="Hello",
            email_from="customer@example.com",
        )

        action = message.reply_message()
        quote_body = action["context"]["quote_body"]
        self.assertIn("--sig--", quote_body)
        self.assertIn("<p>Hello</p>", quote_body)
        self.assertNotIn("<script", quote_body.lower())

    def test_separate_body_parameter_false_values(self):
        self.env["ir.config_parameter"].sudo().set_param(
            "mail_quoted_reply.separate_reply_body", "0"
        )

        partner = self.env["res.partner"].create({"name": "demo partner"})
        message = partner.message_post(
            body="demo message",
            message_type="email",
            partner_ids=self.env.ref("base.partner_demo").ids,
        )
        action = message.reply_message()
        wizard = (
            self.env[action["res_model"]].with_context(**action["context"]).create({})
        )
        wizard._compute_is_separate_body()
        self.assertFalse(wizard.is_separate_body)

    def test_separate_body_sends_reply_plus_quote(self):
        self.env["ir.config_parameter"].sudo().set_param(
            "mail_quoted_reply.separate_reply_body", "True"
        )
        partner = self.env["res.partner"].create({"name": "demo partner"})
        message = partner.message_post(
            body="demo message",
            message_type="email",
            partner_ids=self.env.ref("base.partner_demo").ids,
        )
        action = message.reply_message()
        wizard = (
            self.env[action["res_model"]].with_context(**action["context"]).create({})
        )
        wizard._compute_body()
        wizard.body = "<p>my reply</p>"
        wizard.action_send_mail()

        new_message = partner.message_ids.filtered(
            lambda r: r.message_type != "notification" and r != message
        )
        self.assertEqual(1, len(new_message))
        new_message = new_message[0]
        self.assertIn("<p>my reply</p>", new_message.body)
        self.assertIn("<p>demo message</p>", new_message.body)
        self.assertLess(
            new_message.body.index("<p>my reply</p>"),
            new_message.body.index("<p>demo message</p>"),
        )

    def test_default_partner_created_from_email_from(self):
        partner = self.env["res.partner"].create({"name": "demo partner"})
        message = self._create_message(
            partner,
            body="<p>Hello</p>",
            email_from="New Customer <new.customer@example.com>",
        )
        action = message.reply_message()
        wizard = (
            self.env[action["res_model"]].with_context(**action["context"]).create({})
        )
        self.assertTrue(wizard.partner_ids)
        self.assertIn("new.customer@example.com", wizard.partner_ids.mapped("email"))

    def test_reply_separate_body(self):
        self.env["ir.config_parameter"].sudo().create(
            {
                "key": "mail_quoted_reply.separate_reply_body",
                "value": "True",
            }
        )
        partner = self.env["res.partner"].create({"name": "demo partner"})
        message = partner.message_post(
            body="demo message",
            message_type="email",
            partner_ids=self.env.ref("base.partner_demo").ids,
        )
        partner.invalidate_recordset()
        action = message.reply_message()
        wizard = (
            self.env[action["res_model"]].with_context(**action["context"]).create({})
        )
        wizard._compute_body()
        self.assertTrue("<p>demo message</p>" in wizard.reply_body)
        wizard.action_send_mail()
        new_message = partner.message_ids.filtered(
            lambda r: r.message_type != "notification" and r != message
        )
        self.assertTrue(new_message)
        self.assertEqual(1, len(new_message))
        new_message = new_message[0]
        self.assertTrue("<p>demo message</p>" in new_message.body)
