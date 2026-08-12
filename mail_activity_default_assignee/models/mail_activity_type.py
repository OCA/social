# Copyright 2024 Camptocamp
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class MailActivityType(models.Model):
    _inherit = "mail.activity.type"

    default_user_field_id = fields.Many2one(
        "ir.model.fields",
        help="Default assignee is set based on this field",
    )

    @api.constrains("default_user_field_id")
    def _check_default_user_field_id(self):
        for rec in self:
            if rec.default_user_field_id.model_id.model != rec.res_model:
                raise ValidationError(
                    _(
                        f"{rec.default_user_field_id.field_description} "
                        f"does not exist in model {rec.res_model} "
                    )
                )
