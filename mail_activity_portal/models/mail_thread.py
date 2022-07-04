# © 2022 initOS GmbH
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models


class MailThread(models.AbstractModel):
    _inherit = "mail.thread"

    def schedule_email_activity(self):
        # Thread needs mail.activity.mixin
        if not self or "activity_ids" not in self._fields:
            return

        # Skip if there is no team
        domain = [("res_model_ids.model", "=", self._name)]
        team = self.env["mail.activity.team"].sudo().search(domain, limit=1)
        user = team.user_id or team.member_ids
        if not team or not user:
            return

        activity_type = self.env.ref("mail.mail_activity_data_email")
        for thread in self:
            domain = [
                ("res_model", "=", thread._name),
                ("res_id", "=", thread.id),
                ("automated", "=", True),
                ("activity_type_id", "=", activity_type.id),
            ]
            if self.env["mail.activity"].search(domain):
                continue

            # Schedule the new email activity
            thread.activity_schedule(
                "mail.mail_activity_data_email",
                user_id=user[0].id,
                team_id=team.id,
                automated=True,
            )
