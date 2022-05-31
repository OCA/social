# Copyright 2016-22 PESOL
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
from odoo import api, fields, models


class MailActivityTypeAction(models.Model):
    _name = "mail.activity.type.action"
    _description = "Mail Activity Action"
    _order = "sequence"

    mail_activity_type_id = fields.Many2one(comodel_name="mail.activity.type")
    res_model = fields.Char(compute="_compute_res_model")
    sequence = fields.Integer()
    filter_domain = fields.Char(
        string="Domain",
        help="If present, this condition must be satisfied before the execute server action.",
    )
    auto_action_id = fields.Many2one(
        comodel_name="ir.actions.server",
        domain="[('model_id.model', '=', res_model)]",
    )

    @api.depends("mail_activity_type_id.res_model")
    def _compute_res_model(self):
        for record in self:
            record.res_model = record.mail_activity_type_id.res_model
