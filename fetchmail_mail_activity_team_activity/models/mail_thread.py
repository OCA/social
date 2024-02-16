# © 2022 initOS GmbH
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, models


class MailThread(models.AbstractModel):
    _inherit = "mail.thread"

    @api.model
    def message_route(
        self, message, message_dict, model=None, thread_id=None, custom_values=None
    ):
        # Called by fetchmail module on mail.threads with received emails
        routes = super().message_route(
            message,
            message_dict,
            model=model,
            thread_id=thread_id,
            custom_values=custom_values,
        )

        for route in routes:
            # routes: list of routes [(model, thread_id, custom_values, user_id, alias)]
            model, thread_id = route[0], route[1]
            mdl = self.env[model]
            # Model needs mail.activity.mixin
            if not all(hasattr(mdl, x) for x in ("activity_ids", "activity_schedule")):
                continue

            # Skip if there is no team
            domain = [("res_model_ids.model", "=", model)]
            team = self.env["mail.activity.team"].search(domain, limit=1)
            user = team.user_id or team.member_ids
            if not thread_id or not team or not user:
                continue

            thread = mdl.browse(thread_id)

            # Only schedule if there is no email open email activity
            activity_type = self.env.ref("mail.mail_activity_data_email")
            domain = [
                ("res_model", "=", thread._name),
                ("res_id", "=", thread.id),
                ("automated", "=", True),
                ("activity_type_id", "=", activity_type.id),
            ]
            if thread.activity_ids.search(domain):
                continue

            # Schedule the new email activity
            thread.activity_schedule(
                "mail.mail_activity_data_email",
                user_id=user[0].id,
                team_id=team.id,
                automated=True,
            )

        return routes
