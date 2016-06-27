# -*- coding: utf-8 -*-
# © 2016 Savoir-faire Linux
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import base64

from openerp import api, fields, models
from openerp.tools.safe_eval import safe_eval


class EmailTemplate(models.Model):

    _inherit = 'email.template'

    report_line_ids = fields.One2many(
        'email.template.report.line', 'template_id', string='Other Reports')

    @api.model
    def generate_email_batch(self, template_id, res_ids, fields=None):
        results = super(EmailTemplate, self).generate_email_batch(
            template_id, res_ids, fields=fields)

        template = self.browse(template_id)
        report_ext = '.pdf'

        for report_line in template.report_line_ids:
            records = self.env[template.model_id.model].browse(res_ids)

            for rec in records:
                condition = report_line.condition

                if condition and condition.strip():
                    condition_result = self.render_template(
                        condition, template.model, rec.id)

                    if not condition_result or not safe_eval(condition_result):
                        continue

                report_name = self.render_template(
                    report_line.report_name, template.model, rec.id)

                report = report_line.report_template_id
                report_service = report.report_name

                result = self.env['report'].get_pdf(rec, report_service)
                result = base64.b64encode(result)

                if not report_name:
                    report_name = 'report.' + report_service

                if not report_name.endswith(report_ext):
                    report_name += report_ext

                results[rec.id].setdefault('attachments', [])
                results[rec.id]['attachments'].append((report_name, result))

        return results
