# Copyright 2025 ACSONE SA/NV (<http://acsone.eu>)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
from odoo.osv.expression import FALSE_DOMAIN, TRUE_DOMAIN
from odoo.tests.common import TransactionCase


class TestMailTemplate(TransactionCase):
    """
    Tests for mail.template
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))
        cls.Mail = cls.env["mail.mail"]
        cls.report = cls.env.ref("base.report_ir_model_overview")
        cls.mail_template = cls.env.ref(
            "mail_template_conditional_report.mail_template_demo_hello_world"
        )
        cls.mail_template2 = cls.env.ref(
            "mail_template_conditional_report.mail_template_demo_promote"
        )

    def test_email_generation_no_domain(self):
        """
        Ensure the email generation is working without any domain
        :return:
        """
        self.assertFalse(self.mail_template.mail_template_report_ids.filter_domain)
        target_model = self.env.ref("base.model_res_partner")
        mail_mail_id = self.mail_template.send_mail(target_model.id)
        mail = self.Mail.browse(mail_mail_id).exists()
        self.assertTrue(mail)
        self.assertEqual(len(mail.attachment_ids), 1)

    def test_email_generation_with_domain_valid1(self):
        """
        Ensure the email generation is working with a True leaf domain
        :return:
        """
        self.mail_template.mail_template_report_ids.write(
            {
                "filter_domain": TRUE_DOMAIN,
            }
        )
        target_model = self.env.ref("base.model_res_partner")
        mail_mail_id = self.mail_template.send_mail(target_model.id)
        mail = self.Mail.browse(mail_mail_id).exists()
        self.assertTrue(mail)
        self.assertEqual(len(mail.attachment_ids), 1)

    def test_email_generation_with_domain_valid2(self):
        """
        Ensure the email generation is working with a custom valid domain
        :return:
        """
        target_model = self.env.ref("base.model_res_partner")
        self.mail_template.mail_template_report_ids.write(
            {
                "filter_domain": [("name", "=", target_model.name)],
            }
        )
        mail_mail_id = self.mail_template.send_mail(target_model.id)
        mail = self.Mail.browse(mail_mail_id).exists()
        self.assertTrue(mail)
        self.assertEqual(len(mail.attachment_ids), 1)

    def test_email_generation_with_domain_invalid(self):
        """
        Ensure the email generation is working with False leaf domain
        :return:
        """
        self.mail_template.mail_template_report_ids.write(
            {
                "filter_domain": FALSE_DOMAIN,
            }
        )
        target_model = self.env.ref("base.model_res_partner")
        mail_mail_id = self.mail_template.send_mail(target_model.id)
        mail = self.Mail.browse(mail_mail_id).exists()
        self.assertTrue(mail)
        self.assertEqual(len(mail.attachment_ids), 0)

    def test_email_generation_with_domain_mixed(self):
        """
        Ensure the email generation is working with multiple domains
        :return:
        """
        target_model = self.env.ref("base.model_res_partner")
        mail_mail_id = self.mail_template2.send_mail(target_model.id)
        mail = self.Mail.browse(mail_mail_id).exists()
        self.assertTrue(mail)
        # We should have 3 but the second is dropped by the domain
        self.assertEqual(len(mail.attachment_ids), 3 - 1)
