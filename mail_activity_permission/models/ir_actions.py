# Copyright 2023 Hunki Enterprises BV
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from odoo import api, models, tools


class IrActionsAction(models.Model):
    _inherit = "ir.actions.actions"

    @api.model
    @tools.ormcache("frozenset(self.env.user.groups_id.ids)", "model_name")
    def get_bindings(self, model_name):
        """Add bulk activity wizard to models supporting it"""
        result = super().get_bindings(model_name)
        if (
            model_name in self.env
            and self.env["ir.model"]._get(model_name).is_mail_activity
        ):
            action = self.env.ref(
                "mail_activity_permission.action_mail_activity_bulk_assign"
            )
            result["action"].append(action.read()[0])
        return result
