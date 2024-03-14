# Copyright 2021 ACSONE SA/NV (<http://acsone.eu>)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
from odoo import fields, models


class MailTemplateReport(models.Model):
    """
    Model used to define dynamic report generation on email template
    """

    _name = "mail.template.report"
    _description = "Mail template report"

    mail_template_id = fields.Many2one(
        comodel_name="mail.template",
        string="Mail template",
        required=True,
        ondelete="cascade",
    )
    model = fields.Char(related="mail_template_id.model", store=True)
    report_template_id = fields.Many2one(
        comodel_name="ir.actions.report",
        string="Report",
        required=True,
        ondelete="cascade",
    )
    report_name = fields.Char(translate=True)
