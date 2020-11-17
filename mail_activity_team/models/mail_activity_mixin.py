# Copyright 2018 Eficent Business and IT Consulting Services, S.L.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
from odoo import api, models, fields


class MailActivityMixin(models.AbstractModel):
    _inherit = 'mail.activity.mixin'

    activity_team_user_ids = fields.Many2many(
        comodel_name='res.users', string='Responsible Members',
        compute="_compute_activity_team_user_ids",
        search="_search_activity_team_user_ids",
    )

    @api.depends("activity_ids")
    def _compute_activity_team_user_ids(self):
        for rec in self:
            rec.activity_team_user_ids = rec.activity_ids.mapped(
                "team_id.member_ids")

    @api.model
    def _search_activity_team_user_ids(self, operator, operand):
        return [('activity_ids.team_id.member_ids', operator, operand)]
