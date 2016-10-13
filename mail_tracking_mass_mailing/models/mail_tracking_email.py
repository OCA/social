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
        """Inherit this method to link other object to mail.mail.statistics"""
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
        return tracking

    @api.multi
    def _contacts_email_bounced_set(self, reason):
        for tracking_email in self:
            self.env['mail.mass_mailing.contact'].search([
                ('email', '=ilike', tracking_email.recipient_address)
            ]).email_bounced_set(tracking_email, reason)

    @api.multi
    def smtp_error(self, mail_server, smtp_server, exception):
        res = super(MailTrackingEmail, self).smtp_error(
            mail_server, smtp_server, exception)
        self._contacts_email_bounced_set('error')
        return res

    @api.multi
    def event_create(self, event_type, metadata):
        res = super(MailTrackingEmail, self).event_create(event_type, metadata)
        if event_type in {'hard_bounce', 'spam', 'reject'}:
            self._contacts_email_bounced_set(event_type)
        return res
