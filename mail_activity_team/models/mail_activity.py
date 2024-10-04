# Copyright 2018-22 ForgeFlow S.L.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import SUPERUSER_ID, _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.osv.expression import AND


class MailActivity(models.Model):
    _inherit = "mail.activity"

    user_id = fields.Many2one(string="User", required=False)
    team_user_id = fields.Many2one(
        string="Team user", related="user_id", readonly=False
    )

    team_id = fields.Many2one(
        comodel_name="mail.activity.team",
        compute="_compute_team_id",
        index=True,
        readonly=False,
        store=True,
    )

    @api.onchange("team_id")
    def _onchange_team_id(self):
        if self.team_id and self.user_id not in self.team_id.member_ids:
            if self.team_id.user_id:
                self.user_id = self.team_id.user_id
            elif len(self.team_id.member_ids) == 1:
                self.user_id = self.team_id.member_ids
            else:
                self.user_id = self.env["res.users"]

    @api.depends("activity_type_id", "res_model", "user_id")
    def _compute_team_id(self):
        """Fetch the team given the user, the model and the activity type"""
        for activity in self:
            model_id = self.env["ir.model"]._get_id(activity.res_model)
            if activity.team_id:
                # Does the current team still qualify?
                if (
                    (
                        not activity.user_id
                        or activity.user_id in activity.team_id.member_ids
                    )
                    and (
                        not model_id
                        or not activity.team_id.res_model_ids
                        or model_id in activity.team_id.res_model_ids.ids
                    )
                    and (
                        not activity.activity_type_id.default_team_id
                        or activity.team_id == activity.activity_type_id.default_team_id
                    )
                ):
                    continue
            # Does the activity type's default team qualify?
            default_team = activity.activity_type_id.default_team_id
            if (
                default_team
                and (
                    not activity.user_id or activity.user_id in default_team.member_ids
                )
                and (
                    not model_id
                    or not default_team.res_model_ids
                    or model_id in default_team.res_model_ids.ids
                )
            ):
                activity.team_id = default_team
                if not activity.user_id:
                    activity.user_id = activity.team_id.member_ids[:1]
                continue
            if not activity.user_id:
                continue
            domain = [("member_ids", "=", activity.user_id.id)]
            if model_id:
                domain = AND(
                    [
                        domain,
                        [
                            "|",
                            ("res_model_ids", "=", model_id),
                            ("res_model_ids", "=", False),
                        ],
                    ]
                )
            activity.team_id = self.env["mail.activity.team"].search(domain, limit=1)

    @api.constrains("team_id", "user_id")
    def _check_team_and_user(self):
        for activity in self:
            # SUPERUSER is used to put mail.activity on some objects
            # like sale.order coming from stock.picking
            # (for example with exception type activity, with no backorder).
            # SUPERUSER is inactive and then even if you add it
            # to member_ids it's not taken account
            # To not be blocked we must add it to constraint condition.
            # We must consider also users that could be archived but come from
            # an automatic scheduled activity
            if (
                activity.user_id.id != SUPERUSER_ID
                and activity.team_id
                and activity.user_id
                and activity.user_id
                not in activity.team_id.with_context(active_test=False).member_ids
            ):
                raise ValidationError(
                    _(
                        "The assigned user %(user_name)s is "
                        "not member of the team %(team_name)s.",
                        user_name=activity.user_id.name,
                        team_name=activity.team_id.name,
                    )
                )

    def _prepare_next_activity_values(self):
        """Set the default team, and a member from that team as the user"""
        vals = super()._prepare_next_activity_values()
        if vals.get("activity_type_id"):
            activity_type = self.env["mail.activity.type"].browse(
                vals["activity_type_id"]
            )
            team = activity_type.default_team_id
            if team:
                vals["team_id"] = team.id
                if team.member_ids and (
                    not vals.get("user_id")
                    or vals["user_id"] not in team.member_ids.ids
                ):
                    vals["user_id"] = team.member_ids[0].id
        return vals
