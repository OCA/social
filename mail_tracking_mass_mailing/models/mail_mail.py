# Copyright 2016 Antonio Espinosa - <antonio.espinosa@tecnativa.com>
# Copyright 2017 Vicent Cubells - <vicent.cubells@tecnativa.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import api, models


class MailMail(models.Model):
    _inherit = "mail.mail"

    @api.model
    def _tracking_email_prepare(self, partner, email):
        res = super(MailMail, self)._tracking_email_prepare(partner, email)
        res["mail_id_int"] = self.id
        res["mass_mailing_id"] = self.mailing_id.id
        res["mail_stats_id"] = (
            self.mailing_trace_ids[:1].id if self.mailing_trace_ids else False
        )
        return res

    @api.model
    def _get_tracking_url(self):
        # Invalid this tracking image, we have other to do the same
        return False
