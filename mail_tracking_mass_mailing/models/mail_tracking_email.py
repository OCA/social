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
        # Link mail statistics with this tracking
        if tracking.mail_stats_id:
            tracking.mail_stats_id.write(
                self._statistics_link_prepare(tracking))
            # Get partner from mail statistics
            # if mass_mailing_partner addon installed
            if ('partner_id' in tracking.mail_stats_id._fields and
                    tracking.mail_stats_id.partner_id and
                    not tracking.partner_id):
                tracking.partner_id = tracking.mail_stats_id.partner_id.id
        # Add this tracking to mass mailing contacts with this recipient
        self.tracking_ids_recalculate(
            'mail.mass_mailing.contact', 'email', 'tracking_email_ids',
            tracking.recipient_address, new_tracking=tracking)
        return tracking

    @api.multi
    def event_create(self, event_type, metadata):
        res = super(MailTrackingEmail, self).event_create(event_type, metadata)
        for tracking_email in self:
            contacts = self.tracking_ids_recalculate(
                'mail.mass_mailing.contact', 'email', 'tracking_email_ids',
                tracking_email.recipient_address)
            if contacts:
                contacts.email_score_calculate()
        return res
