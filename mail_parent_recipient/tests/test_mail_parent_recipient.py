# Copyright 2018-2022 Camptocamp
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo.addons.mail.tests.common import MailCommon


class TestMailTemplate(MailCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))

        cls.env["ir.config_parameter"].set_param("mail.use_parent_address", True)

        cls.res_partner = cls.env["res.partner"]
        cls.company_test = cls.res_partner.create(
            {
                "name": "company_name_test",
                "email": "company.mail.test@company",
            }
        )
        cls.partner_no_mail = cls.res_partner.create(
            {
                "name": "partner_1",
                "parent_id": cls.company_test.id,
            }
        )
        cls.partner_with_mail = cls.res_partner.create(
            {
                "name": "partner_2",
                "email": "partner.2.mail.test@company",
                "parent_id": cls.company_test.id,
            }
        )
        cls.record = cls.env.ref("base.partner_demo")
        cls.email_template = (
            cls.env["mail.template"]
            .with_context(test_parent_mail_recipient=True)
            .create(
                {
                    "model_id": cls.env["ir.model"]
                    .search([("model", "=", "mail.channel")], limit=1)
                    .id,
                    "name": "Pigs Template",
                    "subject": "${object.name}",
                    "body_html": "${object.description}",
                    "partner_to": "",
                }
            )
        )

    def _get_email_recipient_for(self, partner_to_send_ids):
        self.email_template.partner_to = ",".join(
            [str(partner_id) for partner_id in partner_to_send_ids]
        )
        values = self.email_template.generate_email(self.record.id, ["partner_to"])
        return values["partner_ids"]

    def test_mail_send_to_partner_no_mail(self):
        """Check recipient without email, comapny email is used."""
        recipients = self._get_email_recipient_for(self.partner_no_mail.ids)
        self.assertEqual(recipients, self.company_test.ids)

    def test_mail_send_to_partner_with_mail(self):
        """Check recipient has email, nothing is changed."""
        recipients = self._get_email_recipient_for(self.partner_with_mail.ids)
        self.assertEqual(recipients, self.partner_with_mail.ids)

    def test_mail_send_to_company_test(self):
        """Check company email is used."""
        recipients = self._get_email_recipient_for(self.company_test.ids)
        self.assertEqual(recipients, self.company_test.ids)

    def test_mail_send_to_company_and_partner_no_mail(self):
        """Check a partner is not add twice in recipient list."""
        recipients = self._get_email_recipient_for(
            [self.partner_no_mail.id, self.company_test.id]
        )
        self.assertEqual(recipients, self.company_test.ids)
