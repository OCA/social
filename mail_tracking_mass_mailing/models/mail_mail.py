# -*- coding: utf-8 -*-
# © 2016 Antonio Espinosa - <antonio.espinosa@tecnativa.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from openerp import models, api


class MailMail(models.Model):
    _inherit = "mail.mail"

    @api.model
    def _tracking_email_prepare(self, mail, partner, email):
        res = super(MailMail, self)._tracking_email_prepare(
            mail, partner, email)
        res['mail_id_int'] = mail.id
        res['mass_mailing_id'] = mail.mailing_id.id
        res['mail_stats_id'] = mail.statistics_ids[:1].id \
            if mail.statistics_ids else False
        return res

    @api.model
    def _get_tracking_url(self, mail, partner=None):
        # Invalid this tracking image, we have other to do the same
        return False
