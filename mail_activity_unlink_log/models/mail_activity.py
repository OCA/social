# Copyright 2023 CreuBlanca
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import models


class MailActivity(models.Model):
    _inherit = "mail.activity"

    def _action_done(self, *args, **kwargs):
        return super(
            MailActivity, self.with_context(activity_unlink_no_message=True)
        )._action_done(*args, **kwargs)

    def unlink(self):
        if not self.env.context.get("activity_unlink_no_message"):
            for activity in self:
                record = self.env[activity.res_model].browse(activity.res_id)
                record.message_post_with_view(
                    "mail_activity_unlink_log.message_activity_unlink",
                    values={
                        "activity": activity,
                        "display_assignee": activity.user_id != self.env.user,
                    },
                    subtype_id=self.env["ir.model.data"]._xmlid_to_res_id(
                        "mail_activity_unlink_log.mt_activities_unlink"
                    ),
                    mail_activity_type_id=activity.activity_type_id.id,
                )
        return super().unlink()


class MailActivityMixin(models.AbstractModel):
    _inherit = "mail.activity.mixin"

    def unlink(self):
        return super(
            MailActivityMixin, self.with_context(activity_unlink_no_message=True)
        ).unlink()
