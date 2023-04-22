# Copyright 2020 Brainbean Apps (https://brainbeanapps.com)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from datetime import datetime, time

from dateutil.relativedelta import relativedelta
from pytz import UTC, timezone

from odoo import _, api, fields, models


class MailActivity(models.Model):
    _inherit = "mail.activity"

    next_reminder = fields.Datetime(
        string="Next reminder",
        compute="_compute_next_reminder",
        compute_sudo=True,
        store=True,
    )
    last_reminder_local = fields.Datetime(string="Last reminder (local)",)
    deadline = fields.Datetime(
        string="Deadline", compute="_compute_deadline", compute_sudo=True, store=True,
    )

    @api.model
    def _get_activities_to_remind_domain(self):
        """Hook for extensions"""
        return [
            ("next_reminder", "<=", fields.Datetime.now()),
            ("deadline", ">=", fields.Datetime.now()),
        ]

    @api.model
    def _get_activities_to_remind(self):
        return self.search(self._get_activities_to_remind_domain())

    @api.model
    def _process_reminders(self):
        activities = self._get_activities_to_remind()
        activities.action_remind()
        return activities

    @api.depends(
        "user_id.tz", "activity_type_id.reminders", "deadline", "last_reminder_local",
    )
    def _compute_next_reminder(self):
        now = fields.Datetime.now()
        for activity in self:
            if activity.deadline < now:
                activity.next_reminder = None
                continue
            reminders = activity.activity_type_id._get_reminder_offsets()
            if not reminders:
                activity.next_reminder = None
                continue
            reminders.sort(reverse=True)
            tz = timezone(activity.user_id.sudo().tz or "UTC")
            last_reminder_local = (
                tz.localize(activity.last_reminder_local)
                if activity.last_reminder_local
                else None
            )
            local_deadline = tz.localize(
                datetime.combine(
                    activity.date_deadline,
                    time.min,  # Schedule reminder based of beginning of day
                )
            )
            for reminder in reminders:
                next_reminder_local = local_deadline - relativedelta(days=reminder,)
                if not last_reminder_local or next_reminder_local > last_reminder_local:
                    break
            if last_reminder_local and next_reminder_local <= last_reminder_local:
                activity.next_reminder = None
                continue
            activity.next_reminder = next_reminder_local.astimezone(UTC).replace(
                tzinfo=None
            )

    @api.depends("user_id.tz", "date_deadline")
    def _compute_deadline(self):
        for activity in self:
            tz = timezone(activity.user_id.sudo().tz or "UTC")
            activity.deadline = (
                tz.localize(datetime.combine(activity.date_deadline, time.max))
                .astimezone(UTC)
                .replace(tzinfo=None)
            )

    def action_notify(self):
        super().action_notify()
        utc_now = fields.Datetime.now().replace(tzinfo=UTC)
        for activity in self:
            if activity.last_reminder_local:
                continue
            tz = timezone(activity.user_id.sudo().tz or "UTC")
            activity.last_reminder_local = utc_now.astimezone(tz).replace(tzinfo=None)

    def action_remind(self):
        """
            Group reminders by user and type and send them together
        """
        MailThread = self.env["mail.thread"]
        message_activity_assigned = self.env.ref(
            "mail_activity_reminder.message_activity_assigned"
        )
        utc_now = fields.Datetime.now().replace(tzinfo=UTC)
        for user in self.mapped("user_id"):
            activities = self.filtered(lambda activity: activity.user_id == user)
            tz = timezone(user.sudo().tz or "UTC")
            local_now = utc_now.astimezone(tz)

            subject = _("Some activities you are assigned too expire soon.")

            body = message_activity_assigned.render(
                dict(activities=activities, model_description="Activities"),
                engine="ir.qweb",
                minimal_qcontext=True,
            )
            MailThread.message_notify(
                partner_ids=user.partner_id.ids,
                body=body,
                subject=subject,
                model_description="Activity",
                notif_layout="mail.mail_notification_light",
            )
            activities.update({"last_reminder_local": local_now.replace(tzinfo=None)})
