# Copyright 2021 Tecnativa - David Vidal
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
from odoo import api, fields, models


class MailActivityMixin(models.AbstractModel):
    _inherit = "mail.activity.mixin"

    activity_team_user_ids = fields.Many2many(
        comodel_name="res.users",
        string="test field",
        compute="_compute_activity_team_user_ids",
        search="_search_activity_team_user_ids",
    )

    @api.depends("activity_ids")
    def _compute_activity_team_user_ids(self):
        for rec in self:
            rec.activity_team_user_ids = rec.activity_ids.mapped("team_id.member_ids")

    def _search_my_activity_date_deadline(self, operator, operand):
        if not self._context.get("team_activities", False):
            return super(MailActivityMixin, self)._search_my_activity_date_deadline(
                operator, operand
            )
        activity_ids = self.env["mail.activity"]._search(
            [
                "|",
                ("user_id", "=", self.env.user.id),
                "&",
                ("date_deadline", operator, operand),
                ("res_model", "=", self._name),
            ]
        )
        return [("activity_ids", "in", activity_ids)]

    @api.model
    def _search_activity_team_user_ids(self, operator, operand):
        return [("activity_ids.team_id.member_ids", operator, operand)]

    def activity_schedule(
        self, act_type_xmlid="", date_deadline=None, summary="", note="", **act_values
    ):
        """With automatic activities, the user onchange won't act so we must
        ensure the right group is set and no exceptions are raised due to
        user-team missmatch. We can hook onto `act_values` dict as it's passed
        to the create activity method.
        """
        user_id = act_values.get("user_id")
        if user_id:
            team = (
                self.env["mail.activity"]
                .with_context(
                    default_res_model=self._name,
                )
                ._get_default_team_id(user_id=user_id)
            )
            act_values.update({"team_id": team.id})
        return super().activity_schedule(
            act_type_xmlid=act_type_xmlid,
            date_deadline=date_deadline,
            summary=summary,
            note=note,
            **act_values
        )
