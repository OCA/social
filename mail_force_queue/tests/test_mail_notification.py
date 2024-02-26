# Copyright 2018 Lorenzo Battistini - Agile Business Group
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

import odoo.tests.common as common


class TestMailNotification(common.TransactionCase):
    def setUp(self):
        super(TestMailNotification, self).setUp()

        self.partner_obj = self.env["res.partner"]
        self.env.user.company_id.force_mail_queue = True

    def test_get_signature_footer(self):
        vals = {
            "name": "p1@example.com",
            "email": "p1@example.com",
        }
        partner1 = self.partner_obj.create(vals)

        body = "this is the body"
        subject = "this is the subject"

        res = partner1.message_post(
            subject=subject,
            body=body,
            content_subtype="plaintext",
            partner_ids=[partner1.id],
        )
        mail = self.env["mail.mail"].search([("mail_message_id", "=", res.id)])
        # default behaviour: outgoing mail queued
        self.assertTrue(mail)
        self.assertEqual(mail.state, "outgoing")

        res = partner1.with_context(mail_notify_force_send=True).message_post(
            subject=subject,
            body=body,
            content_subtype="plaintext",
            partner_ids=[partner1.id],
        )
        mail = self.env["mail.mail"].search([("mail_message_id", "=", res.id)])
        # force send immediately: outgoing email is sent and deleted
        self.assertFalse(mail)

        res = partner1.with_context(mail_notify_force_send=False).message_post(
            subject=subject,
            body=body,
            content_subtype="plaintext",
            partner_ids=[partner1.id],
        )
        mail = self.env["mail.mail"].search([("mail_message_id", "=", res.id)])
        # do not send immediately
        self.assertTrue(mail)
        self.assertEqual(mail.state, "outgoing")
