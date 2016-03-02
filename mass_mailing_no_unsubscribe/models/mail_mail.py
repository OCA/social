# -*- coding: utf-8 -*-
# © 2015 ONESTEiN BV (<http://www.onestein.eu>)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from openerp import models, api


class MailMail(models.Model):
    _inherit = 'mail.mail'

    @api.model
    def _get_unsubscribe_url(self, mail, email_to, msg=None):
        if mail.mailing_id.allow_unsubscribe:
            return super(MailMail, self)._get_unsubscribe_url(
                mail, email_to, msg)
        return ""
