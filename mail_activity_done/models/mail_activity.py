# Copyright 2018 Eficent <http://www.eficent.com>
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html).
from odoo import api, fields, models


class MailActivity(models.Model):

    _inherit = 'mail.activity'

    done = fields.Boolean(default=False)
    state = fields.Selection(selection_add=[
        ('done', 'Done')], compute='_compute_state')
    date_done = fields.Date(
        'Completed Date', index=True, readonly=True,
    )

    @api.depends('done')
    def _compute_state(self):
        super(MailActivity, self)._compute_state()
        for record in self.filtered(lambda activity: activity.done):
            record.state = 'done'
