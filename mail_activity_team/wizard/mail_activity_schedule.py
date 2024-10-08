# Copyright 2024 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import api, fields, models


class MailActivitySchedule(models.TransientModel):
    _inherit = "mail.activity.schedule"

    activity_team_user_id = fields.Many2one(
        string="Team user", related="activity_user_id", store=True, readonly=False
    )
    activity_team_id = fields.Many2one(
        "mail.activity.team",
        "Team assigned to",
        compute="_compute_activity_team_id",
        store=True,
        readonly=False,
    )

    @api.depends("activity_type_id")
    def _compute_activity_team_id(self):
        for scheduler in self:
            if scheduler.activity_type_id.default_team_id:
                scheduler.activity_team_id = scheduler.activity_type_id.default_team_id
            elif not scheduler.activity_team_id:
                scheduler.activity_team_id = (
                    self.env["mail.activity"]
                    .with_context(default_res_model=self.sudo().res_model_id.model)
                    ._get_default_team_id(user_id=scheduler.activity_team_user_id.id)
                )

    @api.onchange("activity_team_id")
    def _onchange_activity_team_id(self):
        if (
            self.activity_team_id
            and self.activity_team_user_id not in self.activity_team_id.member_ids
        ):
            if self.activity_team_id.user_id:
                new_user_id = self.activity_team_id.user_id
            elif len(self.activity_team_id.member_ids) == 1:
                new_user_id = self.activity_team_id.member_ids
            else:
                new_user_id = self.env["res.users"]
            self.activity_team_user_id = new_user_id
            self.activity_user_id = new_user_id

    @api.onchange("activity_team_user_id")
    def _onchange_activity_team_user_id(self):
        if not self.activity_team_user_id or (
            self.activity_team_user_id
            and self.activity_team_user_id in self.activity_team_id.member_ids
        ):
            return
        self.activity_team_id = (
            self.env["mail.activity"]
            .with_context(default_res_model=self.sudo().res_model_id.model)
            ._get_default_team_id(user_id=self.activity_team_user_id.id)
        )

    def _action_schedule_activities(self):
        return self._get_applied_on_records().activity_schedule(
            activity_type_id=self.activity_type_id.id,
            automated=False,
            summary=self.summary,
            note=self.note,
            user_id=self.activity_team_user_id.id,
            team_user_id=self.activity_team_user_id.id,
            team_id=self.activity_team_id.id,
            date_deadline=self.date_deadline,
        )
