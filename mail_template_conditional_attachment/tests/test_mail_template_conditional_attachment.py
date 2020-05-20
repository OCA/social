# Copyright 2020 Druidoo - Iván Todorovich
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo.tests.common import TransactionCase


class TestMailTemplateConditionalAttachments(TransactionCase):
    def setUp(self):
        super(TestMailTemplateConditionalAttachments, self).setUp()

        self.mail_template = self.env.ref(
            'mail_template_conditional_attachment.mail_template')
        self.ir_attachment_company = self.env.ref(
            'mail_template_conditional_attachment.ir_attachment_company')
        self.company_partner = self.env['res.partner'].create({
            'name': 'Company Partner',
            'is_company': True,
        })
        self.person_partner = self.env['res.partner'].create({
            'name': 'Employee A',
            'parent_id': self.company_partner.id,
        })

    def test_conditional_attachment(self):
        res = self.mail_template.generate_email(
            res_ids=[self.company_partner.id, self.person_partner.id])
        self.assertEqual(
            res[self.company_partner.id].get('attachment_ids', []),
            self.ir_attachment_company.ids,
            "The conditional attachment should have been attached",
        )
        self.assertEqual(
            res[self.person_partner.id].get('attachment_ids', []),
            [],
            "No conditional attachments should've been added",
        )
