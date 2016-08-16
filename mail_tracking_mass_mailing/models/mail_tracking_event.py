# -*- coding: utf-8 -*-
# © 2016 Antonio Espinosa - <antonio.espinosa@tecnativa.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from openerp import api, fields, models


class MailTrackingEvent(models.Model):
    _inherit = "mail.tracking.event"

    mass_mailing_id = fields.Many2one(
        string="Mass mailing", comodel_name='mail.mass_mailing', readonly=True,
        related='tracking_email_id.mass_mailing_id', store=True)

    @api.model
    def process_open(self, tracking_email, metadata):
        res = super(MailTrackingEvent, self).process_open(
            tracking_email, metadata)
        mail_mail_stats = self.sudo().env['mail.mail.statistics']
        mail_mail_stats.set_opened(mail_mail_ids=[tracking_email.mail_id_int])
        return res

    def _tracking_set_bounce(self, tracking_email, metadata):
        mail_mail_stats = self.sudo().env['mail.mail.statistics']
        mail_mail_stats.set_bounced(mail_mail_ids=[tracking_email.mail_id_int])

    @api.model
    def process_hard_bounce(self, tracking_email, metadata):
        res = super(MailTrackingEvent, self).process_hard_bounce(
            tracking_email, metadata)
        self._tracking_set_bounce(tracking_email, metadata)
        return res

    @api.model
    def process_soft_bounce(self, tracking_email, metadata):
        res = super(MailTrackingEvent, self).process_soft_bounce(
            tracking_email, metadata)
        self._tracking_set_bounce(tracking_email, metadata)
        return res

    @api.model
    def process_reject(self, tracking_email, metadata):
        res = super(MailTrackingEvent, self).process_reject(
            tracking_email, metadata)
        self._tracking_set_bounce(tracking_email, metadata)
        return res

    @api.model
    def process_spam(self, tracking_email, metadata):
        res = super(MailTrackingEvent, self).process_spam(
            tracking_email, metadata)
        self._tracking_set_bounce(tracking_email, metadata)
        return res
