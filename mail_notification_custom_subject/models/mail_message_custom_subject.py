# Copyright 2020 Tecnativa - João Marques
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import _, fields, models


class MailMessageCustomSubject(models.Model):
    _name = "mail.message.custom.subject"
    _description = "Mail Message Custom Subject"

    name = fields.Char(string="Template Name")
    model_id = fields.Many2one(
        comodel_name="ir.model",
        string="Model",
        required=True,
        help="Model where this template applies",
    )
    subtype_ids = fields.Many2many(
        comodel_name="mail.message.subtype",
        string="Applied Subtypes",
        required=True,
    )
    subject_template = fields.Char(
        string="Subject Template",
        required=True,
        help="Subject (placeholders may be used here)",
    )
    position = fields.Selection(
        selection=[
            ("append_before", _("Append Before")),
            ("append_after", _("Append After")),
            ("replace", _("Replace")),
        ],
        string="Position",
        default="replace",
        help="Whether to replace, append at beggining or append at end to other"
        " templates that apply to a given context",
    )
