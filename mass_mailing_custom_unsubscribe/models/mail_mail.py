# -*- coding: utf-8 -*-
# Copyright 2016 Jairo Llopis <jairo.llopis@tecnativa.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from openerp import api, models


class MailMail(models.Model):
    _inherit = 'mail.mail'

    @api.model
    def _get_unsubscribe_url(self, mail, email_to):
        result = super(MailMail, self)._get_unsubscribe_url(mail, email_to)
        token = mail.mailing_id._unsubscribe_token(mail.res_id)
        return "%s&token=%s" % (result, token)
