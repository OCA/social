# Copyright 2016 Savoir-faire Linux
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import base64

from odoo import _, api, fields, models
from odoo.tools.safe_eval import safe_eval
from odoo.exceptions import UserError


class MailTemplate(models.Model):

    _inherit = 'mail.template'

    report_line_ids = fields.One2many(
        'mail.template.report.line', 'template_id', string='Other Reports')

    @api.model
    def generate_email(self, res_ids, fields=None):
        results = super().generate_email(res_ids, fields=fields)

        for report_line in self.report_line_ids:
            records = self.env[self.model_id.model].browse(res_ids)

            for rec in records:
                condition = report_line.condition

                if condition and condition.strip():
                    condition_result = self._render_template(
                        condition, self.model, rec.id)

                    if not condition_result or not safe_eval(condition_result):
                        continue

                report_name = self._render_template(
                    report_line.report_name, self.model, rec.id)

                report = report_line.report_template_id
                report_service = report.report_name

                if report.report_type in ['qweb-html', 'qweb-pdf']:
                    result, format = report.render_qweb_pdf(rec.ids)
                else:
                    res = report.render(rec.ids)
                    if not res:
                        raise UserError(
                            _('Unsupported report type %s found.') % report.report_type)
                    result, format = res

                result = base64.b64encode(result)

                if not report_name:
                    report_name = 'report.' + report_service
                report_ext = "." + format
                if not report_name.endswith(report_ext):
                    report_name += report_ext

                results[rec.id].setdefault('attachments', [])
                results[rec.id]['attachments'].append((report_name, result))

        return results
