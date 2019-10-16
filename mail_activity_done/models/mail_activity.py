# Copyright 2018-20 ForgeFlow <http://www.forgeflow.com>
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html).
from odoo import api, fields, models


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


class MailActivityMixin(models.AbstractModel):

    _inherit = "mail.activity.mixin"
    activity_ids = fields.One2many(
        domain=lambda self: [("res_model", "=", self._name), ("active", "=", True)]
    )
