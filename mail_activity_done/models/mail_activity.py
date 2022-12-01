# Copyright 2018-20 ForgeFlow <http://www.forgeflow.com>
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html).
from odoo import api, fields, models

delete_sentinel = object()


class MailActivity(models.Model):

    _inherit = "mail.activity"

    active = fields.Boolean(default=True)
    done = fields.Boolean(default=False)
    state = fields.Selection(selection_add=[("done", "Done")], compute="_compute_state")
    date_done = fields.Date("Completed Date", index=True, readonly=True)

    @api.depends("date_deadline", "done")
    def _compute_state(self):
        super()._compute_state()
        for record in self.filtered(lambda activity: activity.done):
            record.state = "done"

    def unlink(self):
        """Don't unlink if we're asked not to"""
        if self.env.context.get("mail_activity_done") != delete_sentinel:
            return super().unlink()

    def _action_done(self, feedback=False, attachment_ids=None):
        """Ask super not to delete the activity and set it to done"""
        self.write({"done": True, "active": False, "date_done": fields.Date.today()})
        return super(
            MailActivity, self.with_context(mail_activity_done=delete_sentinel),
        )._action_done(feedback=feedback, attachment_ids=attachment_ids)


class MailActivityMixin(models.AbstractModel):

    _inherit = "mail.activity.mixin"
    activity_ids = fields.One2many(
        domain=lambda self: [("res_model", "=", self._name), ("active", "=", True)]
    )
