# Copyright 2023 Solvti sp. z o.o. (https://solvti.pl)

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools.safe_eval import safe_eval


class MailTemplateRule(models.Model):
    _name = "mail.template.rule"
    _description = "Mail Template Rule"

    name = fields.Char()
    model_id = fields.Many2one("ir.model", required=True, ondelete="cascade")
    model_name = fields.Char(
        related="model_id.model",
        string="Model Name",
        help="Technical relation required by field_domain",
    )
    company_id = fields.Many2one("res.company", default=lambda self: self.env.company)
    template_id = fields.Many2one(
        "mail.template", required=True, domain="[('model_id', '=', model_id)]"
    )
    field_domain = fields.Char(string="Field Expression")
    active = fields.Boolean(default=True)
    sequence = fields.Integer(default=10)
    context_flag = fields.Char()

    @api.onchange("field_domain")
    def onchange_field_domain(self):
        for rec in self:
            # if the domain translates to False we want to get rid of default "[]"
            # to get the right ordering of the rules
            if not safe_eval(rec.field_domain):
                rec.field_domain = False

    @api.constrains("template_id", "model_id")
    def check_template_company(self):
        for rec in self:
            if rec.template_id.model_id != rec.model_id:
                raise ValidationError(
                    _("The Model of email template is differend then rule Model!")
                )

    @api.onchange("model_id")
    def onchange_model_id(self):
        for rec in self:
            rec.template_id = rec.field_domain = False
