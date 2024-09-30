# Copyright 2024 Tecnativa - Víctor Martínez
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class MailActivityPlan(models.Model):
    _name = "mail.activity.plan"
    _order = "sequence,name,id"
    _description = "Mail Activity Plan"

    active = fields.Boolean(default=True)
    name = fields.Char(required=True)
    sequence = fields.Integer(required=True, default=10)
    model = fields.Char(
        compute="_compute_model", string="Model name", compute_sudo=True, store=True
    )
    model_id = fields.Many2one(
        comodel_name="ir.model",
        domain=[("transient", "=", False), ("model", "not like", "ir.")],
    )
    company_id = fields.Many2one(
        comodel_name="res.company",
        string="Company",
        store=True,
        index=True,
    )
    active = fields.Boolean(default=True)
    group_ids = fields.Many2many(
        comodel_name="res.groups", domain=[("share", "=", False)], string="Groups"
    )
    plan_activity_type_ids = fields.Many2many(
        comodel_name="mail.activity.plan.activity.type",
        domain="[('model', '=', model)]",
        string="Activities",
    )

    @api.depends("model_id")
    def _compute_model(self):
        for item in self:
            item.model = item.model_id.model or False

    @api.model
    def get_total_plans_from_model(self, model):
        return len(self._get_plans_from_model(model))

    def _get_plans_from_model(self, model):
        plans = plan_model = self.env["mail.activity.plan"]
        items = plan_model.search([("model", "=", model)])
        user_groups = self.env.user.groups_id
        for item in items:
            if not item.group_ids or any(g in user_groups for g in item.group_ids):
                plans += item
        return plans


class MailActivityPlanActivityType(models.Model):
    _name = "mail.activity.plan.activity.type"
    _description = "Plan activity type"
    _rec_name = "summary"

    company_id = fields.Many2one(
        comodel_name="res.company",
        string="Company",
        store=True,
        index=True,
    )
    activity_type_id = fields.Many2one(
        comodel_name="mail.activity.type",
        string="Activity Type",
        ondelete="restrict",
        domain="['|', ('res_model', '=', model),('res_model', '=', False)]",
    )
    model = fields.Char(readonly=True)
    summary = fields.Char(compute="_compute_summary", store=True, readonly=False)
    user_expression = fields.Char(string="Assigned to expression")
    user_id = fields.Many2one(comodel_name="res.users", string="Assigned to")

    @api.depends("activity_type_id")
    def _compute_summary(self):
        for item in self:
            item.summary = item.activity_type_id.summary or False

    @api.onchange("user_expression")
    def _onchange_user_expression(self):
        for item in self.filtered(lambda x: x.user_expression):
            item.user_id = False

    @api.onchange("user_id")
    def _onchange_user_id(self):
        for item in self.filtered(lambda x: x.user_id):
            item.user_expression = False

    def _prepare_mail_activity_vals(self, record):
        user_id = self.user_id.id
        if self.user_expression:
            # Get value from record, returned as string
            user_id = self.env["mail.render.mixin"]._render_template(
                self.user_expression, record._name, record.ids, engine="inline_template"
            )[record.id]
            if user_id:
                user_id = int(user_id)
            else:
                # render_inline_template() method return only str. we cannot know the
                # name of the field (User for example) to show it in the error message.
                raise UserError(
                    _("No user with the expression %(expression)s for %(record_name)s")
                    % {
                        "expression": self.user_expression,
                        "record_name": record.display_name,
                    }
                )
        return {
            "activity_type_id": self.activity_type_id.id,
            "summary": self.summary,
            "user_id": user_id if user_id else False,
            "date_deadline": self.env["mail.activity"]._calculate_date_deadline(
                self.activity_type_id
            ),
        }
