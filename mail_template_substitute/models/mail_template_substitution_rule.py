# Copyright 2019 ACSONE SA/NV
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class MailTemplateSubstitutionRule(models.Model):
    _name = "mail.template.substitution.rule"
    _description = "Mail Template Substitution Rule"
    _order = "sequence ASC"

    sequence = fields.Integer(default=10)
    mail_template_id = fields.Many2one(
        comodel_name="mail.template", required=True, ondelete="cascade"
    )
    model = fields.Char(related="mail_template_id.model_id.model", store=True)
    domain = fields.Char(required=True, default="[]")
    substitution_mail_template_id = fields.Many2one(
        comodel_name="mail.template",
        required=True,
        ondelete="cascade",
        domain="[('model', '=', model)]",
    )
