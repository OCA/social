# Copyright 2015 ACSONE SA/NV
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo.tests import common


class TestAttachExistingAttachment(common.TransactionCase):
    def setUp(self):
        super().setUp()
        self.partner_obj = self.env["res.partner"]
        self.partner_01 = self.env["res.partner"].create(
            {
                "name": "Partner 1",
                "email": "partner1@example.org",
                "is_company": True,
                "parent_id": False,
            }
        )

    def test_send_email_attachment(self):
        attach1 = self.env["ir.attachment"].create(
            {
                "name": "Attach1",
                "datas": "bWlncmF0aW9uIHRlc3Q=",
                "res_model": "res.partner",
                "res_id": self.partner_01.id,
            }
        )
        vals = {
            "model": "res.partner",
            "partner_ids": [(6, 0, [self.partner_01.id])],
            "res_id": self.partner_01.id,
            "object_attachment_ids": [(6, 0, [attach1.id])],
        }
        mail = self.env["mail.compose.message"].create(vals)
        values = mail.get_mail_values([self.partner_01.id])
        self.assertTrue(attach1.id in values[self.partner_01.id]["attachment_ids"])
