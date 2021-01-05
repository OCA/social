# Copyright 2020 Tecnativa - João Marques
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo.tests import common


class TestMailNotificationCustomSubject(common.TransactionCase):
    def setUp(self):
        super(TestMailNotificationCustomSubject, self).setUp()
        self.partner_1 = self.env["res.partner"].create(
            {
                "name": "Test partner 1",
                "supplier": True,
                "email": "partner1@example.com",
            }
        )
        self.partner_2 = self.env["res.partner"].create(
            {
                "name": "Test partner 2",
                "supplier": True,
                "email": "partner2@example.com",
            }
        )

    def test_email_subject_template_overrides(self):
        self.env["mail.message.custom.subject"].create(
            {
                "name": "Test template 1",
                "model_id": self.env.ref("base.model_res_partner").id,
                "subtype_ids": [
                    (
                        6,
                        0,
                        [
                            self.env.ref("mail.mt_comment").id,
                        ],
                    )
                ],
                "subject_template": "${object.name or 'n/a'} and something more",
            }
        )
        # Send message in partner
        mail_message_1 = self.partner_1.message_post(
            body="Test", subtype="mail.mt_comment"
        )
        # Get message and check subject
        self.assertEquals(mail_message_1.subject, "Test partner 1 and something more")

        # Send message in partner 2
        mail_message_2 = self.partner_2.message_post(
            body="Test", subtype="mail.mt_comment"
        )
        # Get message and check subject
        self.assertEquals(mail_message_2.subject, "Test partner 2 and something more")

        # Explicit subject should also be overwritten
        mail_message_3 = self.partner_2.message_post(
            body="Test", subtype="mail.mt_comment", subject="Test"
        )
        # Get message and check subject
        self.assertEquals(mail_message_3.subject, "Test partner 2 and something more")

    def test_email_subject_template_normal(self):
        self.env["mail.message.custom.subject"].create(
            {
                "name": "Test template 1",
                "model_id": self.env.ref("base.model_res_partner").id,
                "subtype_ids": [
                    (
                        6,
                        0,
                        [
                            self.env.ref("mail.mt_comment").id,
                        ],
                    )
                ],
                "subject_template": "${object.name or 'n/a'} and something more",
            }
        )
        # Send note in partner
        mail_message_1 = self.partner_1.message_post(
            body="Test", subtype="mail.mt_note", subject="Test"
        )
        # Get message and check subject. Subject Template should not apply
        self.assertEquals(mail_message_1.subject, "Test")

    def test_email_subject_template_multi(self):
        self.env["mail.message.custom.subject"].create(
            {
                "name": "Test template 1",
                "model_id": self.env.ref("base.model_res_partner").id,
                "subtype_ids": [
                    (
                        6,
                        0,
                        [
                            self.env.ref("mail.mt_comment").id,
                        ],
                    )
                ],
                "subject_template": "${object.name or 'n/a'} and something more",
            }
        )
        self.env["mail.message.custom.subject"].create(
            {
                "name": "Test template 2",
                "model_id": self.env.ref("base.model_res_partner").id,
                "subtype_ids": [
                    (
                        6,
                        0,
                        [
                            self.env.ref("mail.mt_comment").id,
                        ],
                    )
                ],
                "subject_template": "${object.name or 'n/a'} and something different",
            }
        )
        # Send message in partner
        mail_message_1 = self.partner_1.message_post(
            body="Test", subtype="mail.mt_comment"
        )
        # Get message and check subject
        self.assertEquals(
            mail_message_1.subject, "Test partner 1 and something different"
        )
        self.env["mail.message.custom.subject"].create(
            {
                "name": "Test template 3",
                "model_id": self.env.ref("base.model_res_partner").id,
                "subtype_ids": [
                    (
                        6,
                        0,
                        [
                            self.env.ref("mail.mt_comment").id,
                        ],
                    )
                ],
                "subject_template": "${' and yet something else'}",
                "position": "append_after",
            }
        )
        # Send message in partner
        mail_message_2 = self.partner_1.message_post(
            body="Test", subtype="mail.mt_comment"
        )
        # Get message and check subject
        self.assertEquals(
            mail_message_2.subject,
            "Test partner 1 and something different and yet something else",
        )
        self.env["mail.message.custom.subject"].create(
            {
                "name": "Test template 4",
                "model_id": self.env.ref("base.model_res_partner").id,
                "subtype_ids": [
                    (
                        6,
                        0,
                        [
                            self.env.ref("mail.mt_comment").id,
                        ],
                    )
                ],
                "subject_template": "${'Re: '}",
                "position": "append_before",
            }
        )
        # Send message in partner
        mail_message_3 = self.partner_1.message_post(
            body="Test", subtype="mail.mt_comment"
        )
        # Get message and check subject
        self.assertEquals(
            mail_message_3.subject,
            "Re: Test partner 1 and something different and yet something else",
        )

    def test_email_subject_template_w_original(self):
        self.env["mail.message.custom.subject"].create(
            {
                "name": "Test template 1",
                "model_id": self.env.ref("base.model_res_partner").id,
                "subtype_ids": [
                    (
                        6,
                        0,
                        [
                            self.env.ref("mail.mt_comment").id,
                        ],
                    )
                ],
                "subject_template": "${' and something more'}",
                "position": "append_after",
            }
        )
        # Send message in partner
        mail_message_1 = self.partner_1.message_post(
            body="Test", subtype="mail.mt_comment", subject="Test",
        )
        # Get message and check subject
        self.assertEquals(
            mail_message_1.subject, "Test and something more"
        )

    def test_bad_template_does_not_break(self):
        self.env["mail.message.custom.subject"].create(
            {
                "name": "Test bad template 1",
                "model_id": self.env.ref("base.model_res_partner").id,
                "subtype_ids": [
                    (
                        6,
                        0,
                        [
                            self.env.ref("mail.mt_comment").id,
                        ],
                    )
                ],
                "subject_template": "${obaject.number_a} and something",
                "position": "append_after",
            }
        )
        # Send message in partner
        mail_message_1 = self.partner_1.message_post(
            body="Test", subtype="mail.mt_comment", subject="Test",
        )
        # Get message and check subject
        # No exception should be raised but subject should remain as original.
        self.assertEquals(
            mail_message_1.subject, "Test"
        )

    def test_no_template_default_result(self):
        # Send message in partner
        mail_message_1 = self.partner_1.message_post(
            body="Test", subtype="mail.mt_comment", subject="Test partner 1"
        )
        # Get message and check subject
        # No exception should be raised but subject should remain as original.
        self.assertEquals(
            mail_message_1.subject, "Test partner 1"
        )
