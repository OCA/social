# -*- coding: utf-8 -*-
# © 2016 Antonio Espinosa - <antonio.espinosa@tecnativa.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from openerp import models, fields, api


class MailTrackingEmail(models.Model):
    _inherit = "mail.tracking.email"

    mass_mailing_id = fields.Many2one(
        string="Mass mailing", comodel_name='mail.mass_mailing', readonly=True)
    mail_stats_id = fields.Many2one(
        string="Mail statistics", comodel_name='mail.mail.statistics',
        readonly=True)
    mail_id_int = fields.Integer(string="Mail ID", readonly=True)

    @api.model
    def _statistics_link_prepare(self, tracking):
        return {
            'mail_tracking_id': tracking.id,
        }

    @api.model
    def create(self, vals):
        tracking = super(MailTrackingEmail, self).create(vals)
        if tracking.mail_stats_id:
            tracking.mail_stats_id.write(
                self._statistics_link_prepare(tracking))
            if tracking.mail_stats_id.partner_id and not tracking.partner_id:
                tracking.partner_id = tracking.mail_stats_id.partner_id.id
        return tracking
