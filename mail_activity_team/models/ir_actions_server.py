# Copyright 2023 Camptocamp SA (https://www.camptocamp.com).
# @author Iván Todorovich <ivan.todorovich@camptocamp.com>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


class IrActionsServer(models.Model):
    _inherit = "ir.actions.server"

    activity_team_id = fields.Many2one(
        "mail.activity.team",
        string="Activity Team",
    )

    def _run_action_next_activity(self, eval_context=None):
        # OVERRIDE to force the activity team on scheduled actions
        if self.activity_user_type == "specific" and self.activity_team_id:
            self = self.with_context(force_activity_team=self.activity_team_id)
        return super()._run_action_next_activity(eval_context=eval_context)
