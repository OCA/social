# Copyright 2025 Tecnativa - Víctor Martínez
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import models


class MailActivity(models.Model):
    _inherit = "mail.activity"

    def _action_done(self, feedback=False, attachment_ids=None):
        """Add the context key to avoid sending the canceled activity email when
        marking the activity as done.
        """
        self = self.with_context(skip_mail_activity_cancel_log=True)
        return super()._action_done(feedback=feedback, attachment_ids=attachment_ids)

    def _log_cancel(self):
        """Method for logging a message of subtype "Activities" indicating
        that the activities in `self` have been canceled.
        """
        for model, activity_data in self._classify_by_model().items():
            records_sudo = self.env[model].sudo().browse(activity_data["record_ids"])
            for record_sudo, activity in zip(
                records_sudo, activity_data["activities"], strict=True
            ):
                # Use exists() to avoid creating messages linked to deleted records
                if not record_sudo.exists():
                    continue
                record_sudo.message_post_with_source(
                    "mail_activity_cancel_tracking.message_activity_cancel",
                    author_id=self.env.user.partner_id.id,
                    render_values={
                        "activity": activity,
                        "display_assignee": activity.user_id != self.env.user,
                    },
                    mail_activity_type_id=activity.activity_type_id.id,
                    subtype_xmlid="mail.mt_activities",
                )

    def unlink(self):
        if not self.env.context.get("skip_mail_activity_cancel_log"):
            self._log_cancel()
        return super().unlink()
