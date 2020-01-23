# Copyright 2016 Savoir-faire Linux
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class MailTemplateReportLine(models.Model):
    """Mail Template Report Line"""

    _name = 'mail.template.report.line'
    _description = __doc__

    template_id = fields.Many2one(
        'mail.template', string='Mail Template'
    )

    report_name = fields.Char(
        'Report Filename', translate=True,
        help="Name to use for the generated report "
        "file (may contain placeholders)\n"
        "The extension can be omitted and will then come from the report type."
    )

    condition = fields.Char(
        'Condition',
        help="An expression evaluated to determine if the report is "
        "to be attached to the email. If blank, the report will always be "
        "attached."
    )

    report_template_id = fields.Many2one(
        'ir.actions.report',
        'Optional report to print and attach',
        domain=[('report_type', 'in', ['qweb-html', 'qweb-pdf'])],
    )
