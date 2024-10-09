from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged("post_install", "-at_install")
class TestMailTracking(TransactionCase):
    def setUp(self):
        super().setUp()
        self.company = self.env.ref("base.main_company")
        self.user = self.env.ref("base.user_demo")
        self.partner = self.env["res.partner"].create(
            {
                "name": "Test Partner",
            }
        )
        self.partner_email_field = self.env["ir.model.fields"].search(
            [("name", "=", "email"), ("model", "=", "res.partner")]
        )
        self.message = self.env["mail.message"].create(
            {
                "subject": "Message test",
                "author_id": self.user.id,
                "message_type": "notification",
                "subtype_id": self.env.ref("mail.mt_note").id,
                "model": "res.partner",
                "res_id": self.partner.id,
            }
        )

        self.tracking_values = self.env["mail.tracking.value"].create(
            {
                "field": self.partner_email_field.id,
                "field_desc": "Email",
                "field_type": "char",
                "old_value_char": "",
                "new_value_char": "test@companytest.com",
                "mail_message_id": self.message.id,
                "company_id": self.company.id,
            }
        )
        self.tracking_values2 = self.env["mail.tracking.value"].create(
            {
                "field": self.partner_email_field.id,
                "field_desc": "Email",
                "field_type": "char",
                "old_value_char": "test@companytest.com",
                "new_value_char": "test10@companytest.com",
                "mail_message_id": self.message.id,
                "company_id": False,
            }
        )

    def test_message_form(self):
        self.assertEqual(len(self.message.tracking_value_ids), 2)
        self.assertEqual(
            self.message.tracking_value_ids[0].company_id.id, self.company.id
        )
        format = self.message.with_context(
            {"company_id": self.company.id, "allowed_company_ids": [self.company.id]}
        )._message_format(self.message._get_message_format_fields())[-1]
        self.assertEqual(len(format["tracking_value_ids"]), 2)
