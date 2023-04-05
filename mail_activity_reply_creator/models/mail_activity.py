# Copyright 2023 Ooops404
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
from odoo import api, models


class MailActivity(models.Model):
    _inherit = "mail.activity"

    @api.onchange("activity_type_id")
    def _onchange_activity_type_id(self):
        original_user_id = self.user_id
        super()._onchange_activity_type_id()
        if (
            original_user_id != self.env.user
            and not self.activity_type_id.default_user_id
        ):
            # keep already set user
            self.user_id = original_user_id

    def action_feedback_schedule_next(self, feedback=False):
        create_uid = self.create_uid.id
        action = super().action_feedback_schedule_next(feedback)
        action["context"]["source_activity_create_uid"] = create_uid
        return action

    @api.model
    def default_get(self, fields):
        res = super().default_get(fields)
        if self._context.get("source_activity_create_uid") and not self.env.context.get(
            "no_recursion"
        ):
            default_activity_type_id = self.with_context(
                no_recursion=True
            )._default_activity_type_id()
            if (
                not default_activity_type_id
                or not default_activity_type_id.default_user_id
            ):
                # assign to prev. activity creator
                res["user_id"] = self.env.context["source_activity_create_uid"]
        return res
