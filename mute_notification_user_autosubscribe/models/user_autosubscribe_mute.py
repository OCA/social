# Copyright 2024 Manuel Regidor <manuel.regidor@sygel.es>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import _, api, fields, models


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

    @api.model
    def is_mute_user(self, model, user):
        mute = False
        user_autosubscribe_mute = self.search([("model_id", "=", model.id)], limit=1)
        if user_autosubscribe_mute:
            groups = (
                ",".join(user_autosubscribe_mute.group_ids.get_external_id().values())
                or ""
            )
            if user.id in user_autosubscribe_mute.user_ids.ids or (
                groups and user.user_has_groups(groups)
            ):
                mute = True
        return mute
