# Copyright 2025 ACSONE SA/NV (<http://acsone.eu>)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
from odoo import fields, models


class MailTemplate(models.Model):
    _inherit = "mail.template"

    mail_template_report_ids = fields.One2many(
        comodel_name="mail.template.report",
        inverse_name="mail_template_id",
        string="Dynamic reports",
    )

    def _generate_template_attachments(
        self, res_ids, render_fields, render_results=None
    ):
        results = super()._generate_template_attachments(
            res_ids, render_fields, render_results=render_results
        )
        self._filter_generated_attachments(results)
        return results

    def _filter_generated_attachments(self, results):
        """
        On given result, check the report should be removed or not.
        :param results: dict
        :return:
        """
        for res_id in results.keys():
            values = results.setdefault(res_id, {})
            attachments = values.pop("attachments", [])
            validated_attachments = []
            for template_report, attachment in zip(
                self.mail_template_report_ids, attachments, strict=True
            ):
                record = self.env[template_report.model_name].browse(res_id)
                if record.filtered_domain(template_report._get_eval_domain()):
                    validated_attachments.append(attachment)
            values.update({"attachments": validated_attachments})
