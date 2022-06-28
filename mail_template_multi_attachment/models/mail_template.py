# Copyright 2021 ACSONE SA/NV (<http://acsone.eu>)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
import base64

from odoo import _, exceptions, fields, models


class MailTemplate(models.Model):
    _inherit = "mail.template"

    template_report_ids = fields.One2many(
        comodel_name="mail.template.report",
        inverse_name="mail_template_id",
    )

    # pylint: disable=redefined-outer-name
    def generate_email(self, res_ids, fields=None):
        """
        Inherit to generate attachments.
        Inspired from original mail.template,generate_email(...) from Odoo.
        :param res_ids: int or list of int
        :param fields:
        :return: dict
        """
        self.ensure_one()
        multi_mode = True
        results = super(MailTemplate, self).generate_email(res_ids, fields=fields)
        if not self.template_report_ids:
            return results
        if isinstance(res_ids, int):
            multi_mode = False
            results = {res_ids: results}
        # Generate attachments (inspired from Odoo); Just add new attachments
        # into 'attachments' key
        for res_id, values in results.items():
            attachments = values.setdefault("attachments", [])
            for template_report in self.template_report_ids:
                report_name = self._render_template(
                    template_report.report_name, template_report.model, res_id
                )
                report = template_report.report_template_id
                report_service = report.report_name

                if report.report_type in ["qweb-html", "qweb-pdf"]:
                    result, report_format = report.render_qweb_pdf([res_id])
                else:
                    res = report.render([res_id])
                    if not res:
                        raise exceptions.UserError(
                            _("Unsupported report type %s found.") % report.report_type
                        )
                    result, report_format = res
                result = base64.b64encode(result)
                if not report_name:
                    report_name = "report." + report_service
                ext = "." + report_format
                if not report_name.endswith(ext):
                    report_name += ext
                attachments.append((report_name, result))
        return multi_mode and results or results[res_ids]
