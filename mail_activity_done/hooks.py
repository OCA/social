# Copyright 2018-22 ForgeFlow <http://www.forgeflow.com>
# Copyright 2018 Odoo, S.A.
# License AGPL-3.0 or later (https://www.gnu.org/licenses/lgpl.html).
from odoo import Command, fields

from odoo.addons.mail.models.mail_activity import MailActivity


def pre_init_hook(cr):
    """The objective of this hook is to default to false all values of field
    'done' of mail.activity
    """
    cr.execute(
        """SELECT column_name
    FROM information_schema.columns
    WHERE table_name='mail_activity' AND
    column_name='done'"""
    )
    if not cr.fetchone():
        cr.execute(
            """
            ALTER TABLE mail_activity ADD COLUMN done boolean;
            """
        )

    cr.execute(
        """
        UPDATE mail_activity
        SET done = False
        """
    )


def post_load_hook():
    def _new_action_done(self, feedback=False, attachment_ids=None):
        """Overwritten method"""
        if "done" not in self._fields:
            return self._action_done_original(
                feedback=feedback, attachment_ids=attachment_ids
            )
        # marking as 'done'
        messages = self.env["mail.message"]
        next_activities_values = []
        for activity in self:
            # extract value to generate next activities
            if activity.chaining_type == "trigger":
                vals = activity.with_context(
                    activity_previous_deadline=activity.date_deadline
                )._prepare_next_activity_values()
                next_activities_values.append(vals)

            # post message on activity, before deleting it
            record = self.env[activity.res_model].browse(activity.res_id)
            activity.done = True
            activity.active = False
            activity.date_done = fields.Date.today()
            record.message_post_with_view(
                "mail.message_activity_done",
                values={
                    "activity": activity,
                    "feedback": feedback,
                    "display_assignee": activity.user_id != self.env.user,
                },
                subtype_id=self.env["ir.model.data"]._xmlid_to_res_id(
                    "mail.mt_activities"
                ),
                mail_activity_type_id=activity.activity_type_id.id,
                attachment_ids=[
                    Command.link(attachment_id) for attachment_id in attachment_ids
                ]
                if attachment_ids
                else [],
            )
            messages |= record.message_ids[0]

        next_activities = self.env["mail.activity"].create(next_activities_values)

        return messages, next_activities

    if not hasattr(MailActivity, "_action_done_original"):
        MailActivity._action_done_original = MailActivity._action_done
        MailActivity._action_done = _new_action_done


def uninstall_hook(cr, registry):
    """The objective of this hook is to remove all activities that are done
    upon module uninstall
    """
    cr.execute(
        """
        DELETE FROM mail_activity
        WHERE done=True
        """
    )
