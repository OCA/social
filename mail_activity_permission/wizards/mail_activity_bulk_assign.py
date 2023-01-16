# Copyright 2022 Hunki Enterprises BV
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from odoo import api, fields, models


class MailActivityBulkAssign(models.TransientModel):
    _name = "mail.activity.bulk.assign"
    _inherit = "mail.activity"
    _description = "Mail activity"

    res_model = fields.Char(default=lambda self: self.env.context.get("active_model"))
    user_ids = fields.Many2many(
        "res.users",
        domain=lambda self: [
            (
                "company_id",
                "=",
                self.env[self.env.context.get("active_model", "base")]
                .browse(self.env.context.get("active_ids", []))
                .mapped("company_id")
                .ids
                + self.env.user.company_id.ids,
            )
        ]
        if "company_id"
        in self.env[self.env.context.get("active_model", "base")]._fields
        else [],
    )
    user_ids_visible = fields.Boolean(compute="_compute_user_ids_visible")

    @api.depends("activity_type_id")
    def _compute_user_ids_visible(self):
        for this in self:
            this.user_ids_visible = not bool(this.activity_type_id.code_user_selection)

    @api.model
    def create(self, vals):
        """Create activities for other selected users"""
        active_model = self.env.context["active_model"]
        active_ids = self.env.context["active_ids"]
        vals.update(
            res_model=active_model,
            res_model_id=self.env["ir.model"]._get_id(active_model),
            res_id=self.env.context.get("active_id"),
        )
        result = super().create(vals)
        vals.pop("user_ids", None)
        for record in self.env[active_model].browse(active_ids):
            activities = self.env["mail.activity"]
            users = result.user_ids
            if result.activity_type_id.code_user_selection:
                users = activities._activity_access_eval(
                    result.activity_type_id.code_user_selection, record._name, record.id
                )
            for user in users:
                activity = self.env["mail.activity"].create(
                    dict(
                        vals,
                        user_id=user.id,
                        res_id=record.id,
                        equivalent_activity_ids=[(6, 0, activities.ids)],
                    )
                )
                activities.write({"equivalent_activity_ids": [(4, activity.id, 0)]})
                activities += activity
        return result
