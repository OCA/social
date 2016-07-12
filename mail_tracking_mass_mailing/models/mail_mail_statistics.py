# -*- coding: utf-8 -*-
# © 2016 Antonio Espinosa - <antonio.espinosa@tecnativa.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from openerp import models, fields, api


class MailMailStatistics(models.Model):
    _inherit = "mail.mail.statistics"

    mail_tracking_id = fields.Many2one(
        string="Mail tracking", comodel_name='mail.tracking.email',
        readonly=True)
    tracking_event_ids = fields.One2many(
        string="Tracking events", comodel_name='mail.tracking.event',
        related='mail_tracking_id.tracking_event_ids', readonly=True)
    tracking_state = fields.Char(
        string="State", compute="_compute_tracking_state", store=True)

    @api.multi
    @api.depends('mail_tracking_id.state')
    def _compute_tracking_state(self):
        for stat in self:
            stat.tracking_state = stat.mail_tracking_id.state
