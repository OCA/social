from odoo.tests.common import TransactionCase


class TestMailComposer(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner_01 = cls.env["res.partner"].create(
            {
                "name": "Partner 1",
                "email": "partner1@example.org",
                "is_company": True,
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

    def test_01_compute_display_object_attachment_ids(self):
        """Test _compute_display_object_attachment_ids"""
        composer = self.env["mail.compose.message"].create(
            {"model": "res.partner", "res_ids": [self.partner_01.id]}
        )

        composer._compute_display_object_attachment_ids()

        # Ensure the computed field contains the expected attachment
        self.assertEqual(len(composer.display_object_attachment_ids), 1)
        self.assertEqual(composer.display_object_attachment_ids, self.attach1)

    def test_02_compute_display_object_attachment_ids_empty(self):
        """Test _compute_display_object_attachment_ids when no res_ids"""
        composer = self.env["mail.compose.message"].create({"model": "res.partner"})

        composer._compute_display_object_attachment_ids()

        self.assertFalse(composer.display_object_attachment_ids)

    def test_03_prepare_mail_values(self):
        """Test _prepare_mail_values() with multiple attachments"""
        attach2 = self.attach1.copy()
        composer = self.env["mail.compose.message"].create(
            {
                "model": "res.partner",
                "res_ids": [self.partner_01.id],
                "object_attachment_ids": (self.attach1 + attach2).ids,
            }
        )

        values = composer._prepare_mail_values([self.partner_01.id])

        self.assertIn(self.attach1.id, values[self.partner_01.id]["attachment_ids"])
        self.assertIn(attach2.id, values[self.partner_01.id]["attachment_ids"])

    def test_04_prepare_mail_values_no_res_ids(self):
        """Test _prepare_mail_values when res_ids is empty"""
        composer = self.env["mail.compose.message"].create(
            {
                "model": "res.partner",
                "object_attachment_ids": self.attach1.ids,
            }
        )

        values = composer._prepare_mail_values([])  # Empty res_ids
        self.assertEqual(values, {})

    def test_05_prepare_mail_values_no_attachments(self):
        """Test _prepare_mail_values when no attachments"""
        composer = self.env["mail.compose.message"].create(
            {
                "model": "res.partner",
                "res_ids": [self.partner_01.id],
            }
        )

        values = composer._prepare_mail_values([self.partner_01.id])

        self.assertEqual(values[self.partner_01.id].get("attachment_ids"), [])
