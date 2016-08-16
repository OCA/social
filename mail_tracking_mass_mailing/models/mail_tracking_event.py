# -*- coding: utf-8 -*-
# © 2016 Antonio Espinosa - <antonio.espinosa@tecnativa.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from openerp import models, api


class MailTrackingEvent(models.Model):
    _inherit = "mail.tracking.event"

    @api.model
    def process_open(self, tracking_email, metadata):
        res = super(MailTrackingEvent, self).process_open(
            tracking_email, metadata)
        mail_mail_stats = self.sudo().env['mail.mail.statistics']
        mail_mail_stats.set_opened(mail_mail_ids=[tracking_email.mail_id_int])
        return res
