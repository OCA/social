# Copyright 2023 Hunki Enterprises BV
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from odoo import api, exceptions, models, tools


class IrModelAccess(models.Model):
    _inherit = "ir.model.access"

    @api.model
    @tools.ormcache_context(
        "self.env.uid",
        "self.env.su",
        "model",
        "mode",
        "raise_exception",
        keys=("lang",),
    )
    def check(self, model, mode="read", raise_exception=True):
        if raise_exception:
            try:
                super().check(model, mode=mode, raise_exception=raise_exception)
            except exceptions.AccessError:
                if not self._check_activity_permission(model, mode):
                    raise
            return True
        return super().check(
            model, mode=mode, raise_exception=raise_exception
        ) or self._check_activity_permission(model, mode)

    @api.model
    def _check_activity_permission(self, model, mode):
        if mode not in ("read", "write"):
            return False
        return bool(
            self.env["mail.activity.type"]
            .sudo()
            .search(
                [
                    "|",
                    ("res_model_id.model", "in", (model, False)),
                    ("field_ids.relation", "=", model),
                    ("perm_%s" % mode, "=", True),
                ]
            )
        )
