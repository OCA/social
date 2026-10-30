# Copyright 2024 Manuel Regidor <manuel.regidor@sygel.es>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import _, fields, models


class UserAutosubscribeMute(models.Model):
    _name = "user.autosubscribe.mute"
    _description = "User Autosubscribe Mute"

    def _get_user_models_domain(self):
        models = (
            self.env["ir.model.fields"]
            .search([("name", "=", "user_id"), ("relation", "=", "res.users")])
            .mapped("model_id")
        )
        return f"[('id', 'in', {models.ids})]"

    name = fields.Char(required=True)
    active = fields.Boolean(default=True)
    model_id = fields.Many2one(
        comodel_name="ir.model",
        domain=_get_user_models_domain,
        ondelete="cascade",
        required=True,
    )
    user_ids = fields.Many2many(comodel_name="res.users", string="Users")
    group_ids = fields.Many2many(comodel_name="res.groups", string="Groups")
    notes = fields.Text()

    _sql_constraints = [
        (
            "unique_model_id",
            "UNIQUE(model_id)",
            _("Model must be unique in User Autosubscribe Mute instances."),
        )
    ]
