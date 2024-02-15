# Copyright 2024 Tecnativa - Víctor Martínez
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl)

from odoo import api, fields, models


class WizardMailActivityPlan(models.TransientModel):
    _name = "wizard.mail.activity.plan"
    _description = "Wizard Mail Activity Plan"

    res_model = fields.Char()
    allowed_activity_plans = fields.Many2many(
        comodel_name="mail.activity.plan",
        compute="_compute_allowed_activity_plans",
    )
    activity_plan_id = fields.Many2one(
        comodel_name="mail.activity.plan",
        domain="[('id', 'in', allowed_activity_plans)]",
        string="Activity Plan",
    )
    detail_ids = fields.One2many(
        comodel_name="wizard.mail.activity.plan.detail",
        inverse_name="parent_id",
        string="Details",
    )

    @api.depends("res_model")
    def _compute_allowed_activity_plans(self):
        plan_model = self.env["mail.activity.plan"]
        for item in self:
            item.allowed_activity_plans = plan_model._get_plans_from_model(
                item.res_model
            )

    @api.onchange("activity_plan_id")
    def _onchange_activity_plan_id(self):
        for item in self:
            details = []
            for res_id in self.env.context.get("active_ids"):
                record = self.env[item.res_model].browse(res_id)
                for activity in item.activity_plan_id.plan_activity_type_ids:
                    detail = activity._prepare_mail_activity_vals(record)
                    detail.update(record_ref="%s,%s" % (record._name, record.id))
                    details.append(detail)
            item.detail_ids = [(5, 0)] + [(0, 0, vals) for vals in details]

    def action_launch(self):
        """Create the activities to the corresponding users.
        Apply sudo to be able to create activities to other users."""
        self.ensure_one()
        activities = self.env["mail.activity"]
        for detail in self.detail_ids:
            record = detail.record_ref
            activities += record.sudo().activity_schedule(
                activity_type_id=detail.activity_type_id.id,
                summary=detail.summary,
                user_id=detail.user_id.id,
                date_deadline=detail.date_deadline,
            )
        return activities


class WizardMailActivityPlanDetail(models.TransientModel):
    _name = "wizard.mail.activity.plan.detail"
    _description = "Wizard Mail Activity Plan Detail"

    parent_id = fields.Many2one(
        comodel_name="wizard.mail.activity.plan",
        string="Parent",
    )
    record_ref = fields.Reference(
        string="Record",
        selection=lambda self: self._get_ref_selection(),
    )
    activity_type_id = fields.Many2one(
        comodel_name="mail.activity.type",
        string="Activity type",
        required=True,
    )
    date_deadline = fields.Date(
        string="Due Date",
        required=True,
    )
    summary = fields.Char()
    user_id = fields.Many2one(
        comodel_name="res.users",
        string="Assigned to",
        required=True,
    )

    @api.model
    def _get_ref_selection(self):
        models = self.env["ir.model"].sudo().search([("transient", "=", False)])
        return [(model.model, model.name) for model in models]
