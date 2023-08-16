# Copyright 2021 ACSONE SA/NV (<http://acsone.eu>)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
from odoo.tests.common import SavepointCase


class TestMailTemplate(SavepointCase):
    """
    Tests for mail.template
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))
        cls.MailTemplate = cls.env["mail.template"]
        cls.partner = cls.env.ref("base.res_partner_12")
        cls.report1 = cls.env.ref("base.report_ir_model_overview")
        cls.report2 = cls.env.ref("base.report_ir_model_overview").copy(
            {"name": cls.report1.name + " Test copy"}
        )
        mail_tmpl_values = {
            "name": "TestTemplate",
            "subject": "About ${object.name}",
            "body_html": "<p>Hello ${object.name}</p>",
            "model_id": cls.env["ir.model"]._get(cls.report1.model).id,
            "report_template": cls.report1.id,
            "report_name": "Report 1",
            "template_report_ids": [
                (
                    0,
                    False,
                    {"report_template_id": cls.report2.id, "report_name": "Report 2"},
                ),
            ],
        }
        cls.mail_template = cls.MailTemplate.create(mail_tmpl_values)

    def test_multi_generation1(self):
        """
        Ensure number of attachment match with what's setup on mail template.
        Don't check the content of the attachment, it's not the purpose
        of this module.
        :return:
        """
        results = self.mail_template.generate_email(self.partner.id, ["body_html"])
        self.assertEqual(2, len(results.get("attachments")))

    def test_multi_generation2(self):
        """
        Ensure the mail generation (standard) still working even without
        template_report_ids
        :return:
        """
        self.mail_template.write({"template_report_ids": [(6, False, [])]})
        results = self.mail_template.generate_email(self.partner.id, ["body_html"])
        self.assertEqual(1, len(results.get("attachments")))

    def test_multi_generation3(self):
        """
        Ensure the mail generation with only template_report_ids filled
        works
        :return:
        """
        self.mail_template.write({"report_template": False, "report_name": False})
        results = self.mail_template.generate_email(self.partner.id, ["body_html"])
        self.assertEqual(1, len(results.get("attachments")))
