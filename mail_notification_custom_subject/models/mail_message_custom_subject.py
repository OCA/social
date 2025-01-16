# Copyright 2020 Tecnativa - João Marques
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import fields, models


class MailMessageCustomSubject(models.Model):
    _name = "mail.message.custom.subject"
    _description = "Mail Message Custom Subject"

    name = fields.Char(string="Template Name")
    model_id = fields.Many2one(
        comodel_name="ir.model",
        string="Model",
        required=True,
        help="Model where this template applies",
        ondelete="cascade",
    )
    subtype_ids = fields.Many2many(
        comodel_name="mail.message.subtype",
        string="Applied Subtypes",
        required=True,
    )
    subject_to_replace = fields.Char(
        help="The text that will be replaced. You can use placeholders."
        " E.g.: {{ object.company_id.name }}"
    )
    subject_template = fields.Char(
        required=True,
        translate=True,
        help="Subject (placeholders may be used here)",
    )
    position = fields.Selection(
        selection=[
            ("append_before", "Append Before"),
            ("append_after", "Append After"),
            ("replace", "Replace"),
            ("inside_replace", "Partial Replacement"),
        ],
        default="replace",
        help="Whether to replace completely, partially, append at beginning or append"
        " at end to other templates that apply to a given context",
    )
