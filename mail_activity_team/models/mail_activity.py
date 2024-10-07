# Copyright 2018 ForgeFlow, S.L.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import SUPERUSER_ID, _, api, fields, models
from odoo.exceptions import ValidationError


class MailActivity(models.Model):
    _inherit = "mail.activity"

    def _get_default_team_id(self, user_id=None):
        if not user_id:
            user_id = self.env.uid
        res_model = self.env.context.get("default_res_model")
        model = self.env["ir.model"].search([("model", "=", res_model)], limit=1)
        domain = [("member_ids", "in", [user_id])]
        if res_model:
            domain.extend(
                ["|", ("res_model_ids", "=", False), ("res_model_ids", "in", model.ids)]
            )
        return self.env["mail.activity.team"].search(domain, limit=1)

    user_id = fields.Many2one(required=False)
    team_user_id = fields.Many2one(related="user_id", readonly=False)

    team_id = fields.Many2one(
        comodel_name="mail.activity.team", default=lambda s: s._get_default_team_id()
    )

    @api.model_create_multi
    def create(self, vals_list):
        vals_list = [
            # ensure that the built-in user_id field value is in sync with our field
            # team_user_id before triggering create
            (
                dict(vals, user_id=vals["team_user_id"])
                if (
                    "user_id" in vals
                    and "team_user_id" in vals
                    and vals["user_id"] != vals["team_user_id"]
                )
                else vals
            )
            for vals in vals_list
        ]
        return super(MailActivity, self).create(vals_list)

    @api.onchange("user_id")
    def _onchange_user_id(self):
        if not self.user_id or (
            self.team_id and self.user_id in self.team_id.member_ids
        ):
            return
        self.team_id = self.with_context(
            default_res_model=self.res_model_id.model
        )._get_default_team_id(user_id=self.user_id.id)

    @api.onchange("team_id")
    def _onchange_team_id(self):
        if self.team_id and self.user_id not in self.team_id.member_ids:
            if self.team_id.user_id:
                self.user_id = self.team_id.user_id
            elif len(self.team_id.member_ids) == 1:
                self.user_id = self.team_id.member_ids
            else:
                self.user_id = self.env["res.users"]

    @api.constrains("team_id", "user_id")
    def _check_team_and_user(self):
        # SUPERUSER is used to put mail.activity on some objects
        # like sale.order coming from stock.picking
        # (for example with exception type activity, with no backorder).
        # SUPERUSER is inactive and then even if you add it
        # to member_ids it's not taken account
        # To not be blocked we must add it to constraint condition
        # We must consider also users that could be archived but come from
        # an automatic scheduled activity
        for _activity in self.filtered(
            lambda a: a.user_id.id != SUPERUSER_ID
            and a.team_id
            and a.user_id
            and a.user_id not in a.team_id.with_context(active_test=True).member_ids
        ):
            raise ValidationError(_("The assigned user is not member of the team."))

    @api.onchange("activity_type_id")
    def _onchange_activity_type_id(self):
        super()._onchange_activity_type_id()
        if self.activity_type_id.default_team_id:
            self.team_id = self.activity_type_id.default_team_id
            members = self.activity_type_id.default_team_id.member_ids
            if self.user_id not in members and members:
                self.user_id = members[:1]
