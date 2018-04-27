# -*- coding: utf-8 -*-
# © 2016 Savoir-faire Linux
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class MailTemplateReportLine(models.Model):
    """Mail Template Report Line"""

    _name = 'mail.template.report.line'
    _description = __doc__

    template_id = fields.Many2one(
        comodel_name='mail.template',
        string='Email Template'
    )

    report_name = fields.Char(
        string='Report Filename',
        translate=True,
        help='Name to use for the generated report '
             'file (may contain placeholders)\n'
             'The extension can be omitted and will '
             'then come from the report type.'
    )

    condition = fields.Char(
        string='Condition',
        help='An expression evaluated to determine if the '
             'report is to be attached to the email. '
             'If blank, the report will always be attached.'
    )

    report_template_id = fields.Many2one(
        comodel_name='ir.actions.report.xml',
        string='Optional report to print and attach',
    )
