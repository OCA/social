# Copyright 2021 DEC SARL, Inc - All Rights Reserved.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import fields, models


class MailTestActivityAlt(models.Model):
    """ This model can be used to test activities in addition to simple chatter
    features. """
    _description = 'Activity Model (Alt)'
    _name = 'mail.test.activity.alt'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char()
    email_from = fields.Char()
    active = fields.Boolean(default=True)

    def action_start(self, action_summary):
        return self.activity_schedule(
            'test_mail.mail_act_test_todo', summary=action_summary
        )

    def action_close(self, action_feedback):
        self.activity_feedback(
            ['test_mail.mail_act_test_todo'], feedback=action_feedback
        )
