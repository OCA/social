# Copyright 2020 Tecnativa - João Marques
# Copyright 2022 Tecnativa - Víctor Martínez
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
# pylint: disable=C8107
from odoo.tests import common
from odoo.tools import mute_logger


class TestMailNotificationCustomSubject(common.TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner_1, cls.partner_2 = (
            cls.env["res.partner"]
            .with_context(tracking_disable=True)
            .create(
                [
                    {"name": "Test partner 1", "email": "partner1@example.com"},
                    {"name": "Test partner 2", "email": "partner2@example.com"},
                ]
            )
        )
        cls.admin = common.new_test_user(cls.env, "boss", "base.group_system")

    def setUp(self):
        super().setUp()
        self.uid = common.new_test_user(self.env, "worker")

    def test_email_subject_template_overrides(self):
        with self.with_user("boss"):
            self.env["mail.message.custom.subject"].create(
                {
                    "name": "Test template 1",
                    "model_id": self.env.ref("base.model_res_partner").id,
                    "subtype_ids": [(6, 0, [self.env.ref("mail.mt_comment").id])],
                    "subject_template": "{{object.name or 'n/a'}} and something more",
                }
            )
        # Send message in partner
        mail_message_1 = self.partner_1.message_post(
            body="Test", subtype_xmlid="mail.mt_comment"
        )
        # Get message and check subject
        self.assertEqual(mail_message_1.subject, "Test partner 1 and something more")

        # Send message in partner 2
        mail_message_2 = self.partner_2.message_post(
            body="Test", subtype_xmlid="mail.mt_comment"
        )
        # Get message and check subject
        self.assertEqual(mail_message_2.subject, "Test partner 2 and something more")

        # Explicit subject should also be overwritten
        mail_message_3 = self.partner_2.message_post(
            body="Test", subtype_xmlid="mail.mt_comment", subject="Test"
        )
        # Get message and check subject
        self.assertEqual(mail_message_3.subject, "Test partner 2 and something more")

    def test_email_subject_template_normal(self):
        with self.with_user("boss"):
            self.env["mail.message.custom.subject"].create(
                {
                    "name": "Test template 1",
                    "model_id": self.env.ref("base.model_res_partner").id,
                    "subtype_ids": [(6, 0, [self.env.ref("mail.mt_comment").id])],
                    "subject_template": "{{object.name or 'n/a'}} and something more",
                }
            )
        # Send note in partner
        mail_message_1 = self.partner_1.message_post(
            body="Test", subtype_xmlid="mail.mt_note", subject="Test"
        )
        # Get message and check subject. Subject Template should not apply
        self.assertEqual(mail_message_1.subject, "Test")

    def test_email_subject_template_multi(self):
        with self.with_user("boss"):
            self.env["mail.message.custom.subject"].create(
                {
                    "name": "Test template 1",
                    "model_id": self.env.ref("base.model_res_partner").id,
                    "subtype_ids": [(6, 0, [self.env.ref("mail.mt_comment").id])],
                    "subject_template": "{{object.name or 'n/a'}} and something more",
                }
            )
        with self.with_user("boss"):
            self.env["mail.message.custom.subject"].create(
                {
                    "name": "Test template 2",
                    "model_id": self.env.ref("base.model_res_partner").id,
                    "subtype_ids": [(6, 0, [self.env.ref("mail.mt_comment").id])],
                    "subject_template": "{{object.name or 'n/a'}} and "
                    "something different",
                }
            )
        # Send message in partner
        mail_message_1 = self.partner_1.message_post(
            body="Test", subtype_xmlid="mail.mt_comment"
        )
        # Get message and check subject
        self.assertEqual(
            mail_message_1.subject, "Test partner 1 and something different"
        )
        with self.with_user("boss"):
            self.env["mail.message.custom.subject"].create(
                {
                    "name": "Test template 3",
                    "model_id": self.env.ref("base.model_res_partner").id,
                    "subtype_ids": [(6, 0, [self.env.ref("mail.mt_comment").id])],
                    "subject_template": "{{' and yet something else'}}",
                    "position": "append_after",
                }
            )
        # Send message in partner
        mail_message_2 = self.partner_1.message_post(
            body="Test", subtype_xmlid="mail.mt_comment"
        )
        # Get message and check subject
        self.assertEqual(
            mail_message_2.subject,
            "Test partner 1 and something different and yet something else",
        )
        with self.with_user("boss"):
            self.env["mail.message.custom.subject"].create(
                {
                    "name": "Test template 4",
                    "model_id": self.env.ref("base.model_res_partner").id,
                    "subtype_ids": [(6, 0, [self.env.ref("mail.mt_comment").id])],
                    "subject_template": "{{'Re: '}}",
                    "position": "append_before",
                }
            )
        # Send message in partner
        mail_message_3 = self.partner_1.message_post(
            body="Test", subtype_xmlid="mail.mt_comment"
        )
        # Get message and check subject
        self.assertEqual(
            mail_message_3.subject,
            "Re: Test partner 1 and something different and yet something else",
        )

    def test_email_subject_template_w_original(self):
        with self.with_user("boss"):
            self.env["mail.message.custom.subject"].create(
                {
                    "name": "Test template 1",
                    "model_id": self.env.ref("base.model_res_partner").id,
                    "subtype_ids": [(6, 0, [self.env.ref("mail.mt_comment").id])],
                    "subject_template": "{{' and something more'}}",
                    "position": "append_after",
                }
            )
        # Send message in partner
        mail_message_1 = self.partner_1.message_post(
            body="Test",
            subtype_xmlid="mail.mt_comment",
            subject="Test",
        )
        # Get message and check subject
        self.assertEqual(mail_message_1.subject, "Test and something more")

    def test_bad_template_does_not_break(self):
        """Create template with error (obaject) to test error."""
        with self.with_user("boss"):
            self.env["mail.message.custom.subject"].create(
                {
                    "name": "Test bad template 1",
                    "model_id": self.env.ref("base.model_res_partner").id,
                    "subtype_ids": [(6, 0, [self.env.ref("mail.mt_comment").id])],
                    "subject_template": "{{obaject.number_a}} and something",
                    "position": "append_after",
                }
            )
        # Send message in partner
        with mute_logger("odoo.addons.mail.models.mail_render_mixin"):
            mail_message_1 = self.partner_1.message_post(
                body="Test",
                subtype_xmlid="mail.mt_comment",
                subject="Test",
            )
        # Get message and check subject
        # No exception should be raised but subject should remain as original.
        self.assertEqual(mail_message_1.subject, "Test")

    def test_no_template_default_result(self):
        # Send message in partner
        mail_message_1 = self.partner_1.message_post(
            body="Test", subtype_xmlid="mail.mt_comment", subject="Test partner 1"
        )
        # Get message and check subject
        # No exception should be raised but subject should remain as original.
        self.assertEqual(mail_message_1.subject, "Test partner 1")
