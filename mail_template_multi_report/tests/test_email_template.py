# -*- coding: utf-8 -*-
# © 2016 Savoir-faire Linux
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from openerp.tests import common


class TestEmailTemplate(common.TransactionCase):

    def setUp(self):
        super(TestEmailTemplate, self).setUp()

        self.report_view = self.env['ir.ui.view'].create({
            'name': 'test_report_template',
            'mode': 'primary',
            'type': 'qweb',
            'arch': """\
<?xml version="1.0"?>
<t t-name="mail_template_multi_report.test_report_template">
    <t t-call="report.html_container">
        <t t-call="report.internal_layout">
            <div class="page">
            </div>
        </t>
    </t>
</t>
            """
        })

        model_data = self.env['ir.model.data'].create({
            'module': 'mail_template_multi_report',
            'model': 'ir.ui.view',
            'name': 'test_report_template',
            'res_id': self.report_view.id,
        })

        model_data.clear_caches()

        self.report = self.env['ir.actions.report.xml'].create({
            'name': 'Test Report 1',
            'model': 'res.partner',
            'report_type': 'qweb-html',
            'report_name': 'mail_template_multi_report.test_report_template',
        })

        self.template = self.env['email.template'].create({
            'name': 'Test Email Template',
            'model_id': self.env.ref('base.model_res_partner').id,
            'report_line_ids': [(0, 0, {
                'report_name': '${object.name}',
                'report_template_id': self.report.id,
            })]
        })

        self.partner = self.env['res.partner'].create({
            'name': 'Test Partner',
            'customer': True,
        })

    def test_01_generate_email_batch(self):
        res = self.env['email.template'].generate_email_batch(
            self.template.id, [self.partner.id])

        self.assertEquals(len(res[self.partner.id]['attachments']), 1)

    def test_02_generate_email_batch_with_standard_report(self):
        self.template.write({
            'report_name': '${object.name}',
            'report_template': self.report.id,
        })

        res = self.env['email.template'].generate_email_batch(
            self.template.id, [self.partner.id])

        self.assertEquals(len(res[self.partner.id]['attachments']), 2)

    def test_03_report_condition_true(self):
        self.template.report_line_ids[0].write({
            'condition': "${object.customer}",
        })

        res = self.env['email.template'].generate_email_batch(
            self.template.id, [self.partner.id])

        self.assertEquals(len(res[self.partner.id]['attachments']), 1)

    def test_04_report_condition_false(self):
        self.template.report_line_ids[0].write({
            'condition': "${object.supplier}",
        })

        res = self.env['email.template'].generate_email_batch(
            self.template.id, [self.partner.id])

        res[self.partner.id].setdefault('attachments', [])
        self.assertEquals(len(res[self.partner.id]['attachments']), 0)
