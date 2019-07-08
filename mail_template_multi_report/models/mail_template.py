# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import base64

from odoo import _, api, fields, models
from odoo.tools import pycompat
from odoo.tools.safe_eval import safe_eval
from odoo.exceptions import UserError


class MailTemplate(models.Model):

    _inherit = 'mail.template'

    report_line_ids = fields.One2many(
        'mail.template.report.line', 'template_id', string='Other Reports')

    @api.multi
    def generate_email(self, res_ids, fields=None):
        res = super(MailTemplate, self).generate_email(res_ids, fields=fields)

        if self.report_line_ids and len(self.report_line_ids):
            multi_mode = True
            if isinstance(res_ids, pycompat.integer_types):
                res_ids = [res_ids]
                multi_mode = False

            for record in self.env[self.model].browse(res_ids):
                attachments = multi_mode and res[record.id].get('attachments', []) or res.get('attachments', [])
                for report_line in self.report_line_ids:
                    condition = report_line.condition
                    if condition and condition.strip():
                        condition_result = self.render_template(condition, self.model, record.id)
                        if not condition_result or not safe_eval(condition_result):
                            continue
                    report_name = self.render_template(report_line.report_name, self.model, record.id)
                    report = report_line.report_template_id
                    report_service = report.report_name
                    if report.report_type not in ['qweb-html', 'qweb-pdf']:
                        raise UserError(_('Unsupported report type %s found.') % report.report_type)
                    result, result_format = report.render_qweb_pdf(record.id)
                    result = base64.b64encode(result)
                    if not report_name:
                        report_name = 'report.' + report_service
                    ext = "." + result_format
                    if not report_name.endswith(ext):
                        report_name += ext
                    attachments.append((report_name, result))
                    if multi_mode:
                        res[record.id]['attachments'] = attachments
                    else:
                        res['attachments'] = attachments

        return res
