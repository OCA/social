# Copyright 2015 ACSONE SA/NV
# Copyright 2024 360ERP (<https://www.360erp.com>)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo.tests.common import Form, TransactionCase


class TestMailComposer(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner_01 = cls.env["res.partner"].create(
            {
                "name": "Partner 1",
                "email": "partner1@example.org",
                "is_company": True,
                "parent_id": False,
            }
        )
        cls.attach1 = cls.env["ir.attachment"].create(
            {
                "name": "Attach1",
                "datas": "bWlncmF0aW9uIHRlc3Q=",
                "res_model": "res.partner",
                "res_id": cls.partner_01.id,
            }
        )

    def test_01_send_email_attachment(self):
        """Test sending amail with attachment from Object Attachment of composer"""
        # Open email composer
        composer_form = Form(
            self.env["mail.compose.message"].with_context(
                default_composition_mode="comment",
                default_model=self.partner_01._name,
                default_res_ids=self.partner_01.ids,
            )
        )

        # Field can_attach_attachment is automatically set
        self.assertTrue(composer_form.can_attach_attachment)

        # By default, no attachments are present
        self.assertFalse(composer_form.partner_ids[:])
        self.assertEqual(len(composer_form.attachment_ids), 0)
        self.assertEqual(len(composer_form.object_attachment_ids), 0)

        # One selectable Object Attachment is displayed
        display_records = composer_form.display_object_attachment_ids._records
        self.assertEqual(len(display_records), 1)
        self.assertEqual(display_records[0]["id"], self.attach1.id)

        # Fill email composer with the Object Attachment
        composer_form.partner_ids = self.partner_01
        composer_form.object_attachment_ids = self.attach1
        mail = composer_form.save()

        # Send email: the attachment is sent
        values = mail._action_send_mail()
        result_message = values[1]
        self.assertEqual(result_message.attachment_ids, self.attach1)

    def test_02_prepare_mail_values(self):
        """Test method _prepare_mail_values()"""
        attach2 = self.attach1.copy()
        # Create email composer with 2 Object Attachments
        composer = (
            self.env["mail.compose.message"]
            .with_context(
                default_composition_mode="comment",
                default_model=self.partner_01._name,
                default_res_ids=self.partner_01.ids,
            )
            .create(
                {
                    "object_attachment_ids": (self.attach1 + attach2).ids,
                }
            )
        )

        # Two selectable Object Attachments are displayed
        display_records = composer.display_object_attachment_ids
        self.assertEqual(len(display_records), 2)
        self.assertIn(self.attach1, display_records)
        self.assertIn(attach2, display_records)

        # Invoking _prepare_mail_values(): both attachment_ids are set
        values = composer._prepare_mail_values(self.partner_01.ids)
        self.assertIn(self.attach1.id, values[self.partner_01.id]["attachment_ids"])
        self.assertIn(attach2.id, values[self.partner_01.id]["attachment_ids"])
