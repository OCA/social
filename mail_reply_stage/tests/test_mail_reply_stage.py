# Copyright 2025 Quartile (https://www.quartile.co)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo_test_helper import FakeModelLoader

from odoo import Command
from odoo.tests.common import TransactionCase


class TestMailReplyStage(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.loader = FakeModelLoader(cls.env, cls.__module__)
        cls.loader.backup_registry()
        from .test_models import TestMailReply, TestMailReplyParent, TestMailReplyStage

        cls.loader.update_registry(
            (TestMailReplyParent, TestMailReply, TestMailReplyStage)
        )
        cls.test_model = cls.env.ref("mail_reply_stage.model_test_mail_reply")
        cls.parent_stage_ids_field = cls.env["ir.model.fields"]._get(
            "test.mail.reply.parent", "stage_ids"
        )
        cls.parent_id_field = cls.env["ir.model.fields"]._get(
            "test.mail.reply", "parent_id"
        )
        cls.reply_stage_id_field = cls.env["ir.model.fields"]._get(
            "test.mail.reply", "stage_id"
        )
        cls.stage_a, cls.stage_a_xmlid = cls.create_stage("Stage A")
        cls.stage_b, cls.stage_b_xmlid = cls.create_stage("Stage B")
        cls.stage_c, cls.stage_c_xmlid = cls.create_stage("Stage C")
        cls.stage_d, cls.stage_d_xmlid = cls.create_stage("Stage D")
        cls.parent_1 = cls.env["test.mail.reply.parent"].create(
            {
                "name": "Test Parent 1",
                "stage_ids": [
                    Command.set([cls.stage_a.id, cls.stage_b.id, cls.stage_c.id])
                ],
            }
        )
        cls.parent_2 = cls.env["test.mail.reply.parent"].create(
            {
                "name": "Test Parent 2",
                "stage_ids": [
                    Command.set([cls.stage_a.id, cls.stage_b.id, cls.stage_c.id])
                ],
            }
        )
        cls.record_1 = cls.env["test.mail.reply"].create(
            {
                "name": "Test 1",
                "parent_id": cls.parent_1.id,
                "stage_id": cls.stage_a.id,
            }
        )
        cls.record_2 = cls.env["test.mail.reply"].create(
            {
                "name": "Test 2",
                "parent_id": cls.parent_2.id,
                "stage_id": cls.stage_a.id,
            }
        )
        cls.mail_reply_config_1 = cls.env["mail.reply.config"].create(
            {
                "model_id": cls.test_model.id,
                "parent_field_id": cls.parent_id_field.id,
                "parent_stage_field_id": cls.parent_stage_ids_field.id,
                "domain": "[('parent_id.name', '=', 'Test Parent 1')]",
                "reply_stage_field_id": cls.reply_stage_id_field.id,
                "reply_stage_xml_id": cls.stage_b_xmlid.id,
            }
        )
        cls.mail_reply_config_2 = cls.env["mail.reply.config"].create(
            {
                "sequence": 20,
                "model_id": cls.test_model.id,
                "parent_field_id": cls.parent_id_field.id,
                "parent_stage_field_id": cls.parent_stage_ids_field.id,
                "reply_stage_field_id": cls.reply_stage_id_field.id,
                "reply_stage_xml_id": cls.stage_c_xmlid.id,
            }
        )
        cls.user = (
            cls.env["res.users"]
            .with_context(no_reset_password=True)
            .create(
                {
                    "name": "Non-Internal User",
                    "login": "test@example.com",
                    "email": "test@example.com",
                    "groups_id": [Command.set([cls.env.ref("base.group_portal").id])],
                }
            )
        )

    @classmethod
    def create_stage(cls, name):
        stage = cls.env["test.mail.reply.stage"].create({"name": name})
        stage._export_rows([["id"]])
        xmlid = cls.env["ir.model.data"].search(
            [("model", "=", "test.mail.reply.stage"), ("res_id", "=", stage.id)]
        )
        return stage, xmlid

    @classmethod
    def tearDownClass(cls):
        cls.loader.restore_registry()
        super().tearDownClass()

    def test_mail_reply_stage_assigned(self):
        self.assertEqual(self.record_1.stage_id, self.stage_a)
        self.record_1.message_post(
            author_id=self.user.partner_id.id,
            subtype_id=self.env.ref("mail.mt_comment").id,
            body="Test mail reply stage.",
        )
        self.assertEqual(self.record_1.stage_id, self.stage_b)
        self.assertEqual(self.record_2.stage_id, self.stage_a)
        self.record_2.message_post(
            author_id=self.user.partner_id.id,
            subtype_id=self.env.ref("mail.mt_comment").id,
            body="Test mail reply stage.",
        )
        self.assertEqual(self.record_2.stage_id, self.stage_c)

    def test_mail_reply_stage_sequence(self):
        self.assertEqual(self.record_1.stage_id, self.stage_a)
        self.mail_reply_config_1.sequence = 30
        self.record_1.message_post(
            author_id=self.user.partner_id.id,
            subtype_id=self.env.ref("mail.mt_comment").id,
            body="Test mail reply stage.",
        )
        self.assertEqual(self.record_1.stage_id, self.stage_c)

    def test_mail_reply_stage_not_assigned(self):
        self.assertEqual(self.record_1.stage_id, self.stage_a)
        # Send as an internal user
        self.record_1.message_post(
            author_id=self.env.user.partner_id.id, body="Test mail reply stage."
        )
        self.assertEqual(self.record_1.stage_id, self.stage_a)
        self.mail_reply_config_1.reply_stage_xml_id = self.stage_d_xmlid.id
        self.mail_reply_config_2.reply_stage_xml_id = self.stage_d_xmlid.id
        self.record_1.message_post(
            author_id=self.user.partner_id.id, body="Test mail reply stage."
        )
        self.assertEqual(self.record_1.stage_id, self.stage_a)
