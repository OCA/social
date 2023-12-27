# Copyright 2021 Camptocamp (http://www.camptocamp.com).
# @author Iván Todorovich <ivan.todorovich@gmail.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class MailAutosubscribe(models.Model):
    _name = "mail.autosubscribe"
    _description = "Mail Autosubscribe"

    _sql_constraints = [
        (
            "model_id_unique",
            "UNIQUE(model_id)",
            "There's already a rule for this model",
        )
    ]

    model_id = fields.Many2one(
        "ir.model",
        required=True,
        index=True,
        ondelete="cascade",
    )
    model = fields.Char(
        related="model_id.model",
        string="Model Name",
        store=True,
        index=True,
    )
    name = fields.Char(
        compute="_compute_name",
        store=True,
        readonly=False,
    )

    @api.depends("model_id")
    def _compute_name(self):
        for rec in self:
            if not rec.name:
                rec.name = rec.model_id.name
