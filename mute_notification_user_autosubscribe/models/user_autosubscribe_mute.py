# Copyright 2024 Manuel Regidor <manuel.regidor@sygel.es>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models
from odoo.fields import Domain


class UserAutosubscribeMute(models.Model):
    _name = "user.autosubscribe.mute"
    _description = "User Autosubscribe Mute"

    def _get_user_models_domain(self):
        domain = Domain("name", "in", ["user_id"]) & Domain(
            "relation", "in", ["res.users"]
        )
        user_models = self.env["ir.model.fields"].search(domain).mapped("model_id")
        return Domain("id", "in", user_models.ids)

    name = fields.Char(required=True)
    active = fields.Boolean(default=True)
    model_id = fields.Many2one(
        comodel_name="ir.model",
        domain=lambda self: self._get_user_models_domain(),
        ondelete="cascade",
        required=True,
    )
    user_ids = fields.Many2many(comodel_name="res.users", string="Users")
    group_ids = fields.Many2many(comodel_name="res.groups", string="Groups")
    notes = fields.Text()

    _unique_model = models.Constraint(
        "unique(model_id)", "Model must be unique in User Autosubscribe Mute instances."
    )
