# Copyright 2018 Eficent Business and IT Consulting Services S.L.
# Copyright 2018 Odoo, S.A.
# License AGPL-3.0 or later (https://www.gnu.org/licenses/lgpl.html).
from odoo.addons.mail.models.mail_activity import MailActivity
from odoo import fields


def pre_init_hook(cr):
    """ The objective of this hook is to default to false all values of field
    'done' of mail.activity
    """
    cr.execute("""SELECT column_name
    FROM information_schema.columns
    WHERE table_name='mail_activity' AND
    column_name='done'""")
    if not cr.fetchone():
        cr.execute(
            """
            ALTER TABLE mail_activity ADD COLUMN done boolean;
            """)

    cr.execute(
        """
        UPDATE mail_activity
        SET done = False
        """
    )


def post_load_hook():

    def new_action_feedback(self, feedback=False):

        if 'done' not in self._fields:
            return self.action_feedback_original(feedback=feedback)
        message = self.env['mail.message']
        if feedback:
            self.write(dict(feedback=feedback))
        for activity in self:
            record = self.env[activity.res_model].browse(activity.res_id)
            activity.done = True
            activity.active = False
            activity.date_done = fields.Date.today()
            record.message_post_with_view(
                'mail.message_activity_done',
                values={'activity': activity},
                subtype_id=self.env.ref('mail.mt_activities').id,
                mail_activity_type_id=activity.activity_type_id.id,
            )
            message |= record.message_ids[0]
        return message.ids and message.ids[0] or False

    if not hasattr(MailActivity, 'action_feedback_original'):
        MailActivity.action_feedback_original = MailActivity.action_feedback
        MailActivity.action_feedback = new_action_feedback


def uninstall_hook(cr, registry):
    """ The objective of this hook is to remove all activities that are done
        upon module uninstall
        """
    cr.execute(
        """
        DELETE FROM mail_activity
        WHERE done=True
        """
    )
