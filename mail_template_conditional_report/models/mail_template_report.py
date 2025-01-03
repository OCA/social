# Copyright 2025 ACSONE SA/NV (<http://acsone.eu>)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
from odoo import fields, models
from odoo.osv.expression import TRUE_DOMAIN
from odoo.tools.safe_eval import datetime, safe_eval


class MailTemplateReport(models.Model):
    """
    Model used to represent existing relation between
    report (ir.actions.report) and mail template (mail.template)
    """

    _name = "mail.template.report"
    _table = "mail_template_ir_actions_report_rel"
    _description = "Mail template report relation"

    mail_template_id = fields.Many2one(
        comodel_name="mail.template",
        string="Mail template",
        required=True,
        ondelete="cascade",
    )
    ir_actions_report_id = fields.Many2one(
        comodel_name="ir.actions.report",
        string="Report",
        required=True,
        ondelete="cascade",
        domain="[('model','=', model_name)]",
    )
    model_name = fields.Char(
        related="mail_template_id.model_id.model",
        store=True,
    )
    filter_domain = fields.Char(
        string="Domain",
        help="Filter/Domain to apply on record to print to know if "
        "the report must be added on the mail.\n"
        "Technically, dynamics reports are always generated and then removed "
        "from attachments if the record doesn't match to the domain.\n"
        "Computed fields can be used (because filtered_domain(...) is used).",
        default=False,
    )

    _sql_constraints = [
        (
            "unique_template_report",
            "unique(mail_template_id, ir_actions_report_id)",
            "The relation between the mail template and the report already exists!",
        ),
    ]

    def _get_eval_domain(self):
        self.ensure_one()
        if not self.filter_domain:
            return TRUE_DOMAIN
        return safe_eval(
            self.filter_domain,
            {
                "user": self.env.user.with_context({}),  # pylint: disable=context-overridden
                "companies": self.env.companies,
                "company": self.env.company,
                "datetime": datetime,
                "context_today": fields.Date.context_today(self),
            },
        )
