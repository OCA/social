# Copyright 2018 ForgeFlow, S.L.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
from odoo import api, fields, models


class MailActivityTeam(models.Model):
    _name = "mail.activity.team"
    _description = "Mail Activity Team"

    @api.depends("res_model_ids", "member_ids")
    def _compute_missing_activities(self):
        activity_model = self.env["mail.activity"]
        for team in self:
            domain = [("team_id", "=", False)]
            if team.member_ids:
                domain.append(("user_id", "in", team.member_ids.ids))
            if team.res_model_ids:
                domain.append(("res_model_id", "in", team.res_model_ids.ids))
            team.count_missing_activities = activity_model.search(domain, count=True)

    name = fields.Char(string="Name", required=True, translate=True)
    active = fields.Boolean(string="Active", default=True)
    res_model_ids = fields.Many2many(
        comodel_name="ir.model",
        string="Used models",
        domain=lambda self: [
            (
                "model",
                "in",
                [
                    k
                    for k in self.env.registry
                    if issubclass(
                        type(self.env[k]), type(self.env["mail.activity.mixin"])
                    )
                    and self.env[k]._auto
                ],
            )
        ],
    )
    member_ids = fields.Many2many(
        comodel_name="res.users",
        relation="mail_activity_team_users_rel",
        string="Team Members",
    )
    user_id = fields.Many2one(comodel_name="res.users", string="Team Leader")
    count_missing_activities = fields.Integer(
        string="Missing Activities", compute="_compute_missing_activities", default=0
    )

    @api.onchange("member_ids")
    def _onchange_member_ids(self):
        """Remove team leader in case is not a member anymore"""
        if self.user_id and self.user_id not in self.member_ids:
            self.user_id = False

    @api.onchange("user_id")
    def _onchange_user_id(self):
        if self.user_id and self.user_id not in self.member_ids:
            members_ids = self.member_ids.ids
            members_ids.append(self.user_id.id)
            self.member_ids = [(4, member) for member in members_ids]

    def assign_team_to_unassigned_activities(self):
        activity_model = self.env["mail.activity"]
        for team in self:
            domain = [("team_id", "=", False)]
            if team.member_ids:
                domain.append(("user_id", "in", team.member_ids.ids))
            if team.res_model_ids:
                domain.append(("res_model_id", "in", team.res_model_ids.ids))
            missing_activities = activity_model.search(domain)
            for missing_activity in missing_activities:
                missing_activity.write({"team_id": team.id})
