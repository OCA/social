# -*- coding: utf-8 -*-
# © 2016 Savoir-faire Linux
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
import base64

from odoo import api, fields, models
from odoo.tools.safe_eval import safe_eval
from odoo import report as odoo_report


class MailTemplate(models.Model):

    _inherit = 'mail.template'

    report_line_ids = fields.One2many(
        comodel_name='mail.template.report.line',
        inverse_name='template_id',
        string='Other Reports'
    )

    @api.multi
    def generate_email(self, res_ids, fields=None):

        self.ensure_one()

        results = super(MailTemplate, self).generate_email(
            res_ids, fields=fields)

        for report_line in self.report_line_ids:
            records = self.env[self.model_id.model].browse(res_ids)

            for rec in records:
                condition = report_line.condition

                if condition and condition.strip():
                    condition_result = self.render_template(
                        condition, self.model, rec.id)

                    if not condition_result or not safe_eval(condition_result):
                        continue

                report_name = self.render_template(
                    report_line.report_name, self.model, rec.id)

                report = report_line.report_template_id

                report_service = report.report_name

                if report.report_type in ['qweb-html', 'qweb-pdf']:
                    result, fmt = self.env['report'].get_pdf(
                        [rec.id], report_service), 'pdf'
                else:
                    result, fmt = odoo_report.render_report(
                        self._cr, self._uid, [rec.id],
                        report_service, {'model': self.model}, self._context)

                result = base64.b64encode(result)

                ext = "." + fmt

                if not report_name:
                    report_name = 'report.' + report_service

                if not report_name.endswith(ext):
                    report_name += ext

                results[rec.id].setdefault('attachments', [])
                results[rec.id]['attachments'].append((report_name, result))

        return results
