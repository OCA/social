# -*- coding: utf-8 -*-
# Copyright 2016 Jairo Llopis <jairo.llopis@tecnativa.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from openerp import models


class MailMail(models.Model):
    _inherit = 'mail.mail'

    def _get_unsubscribe_url(self, email_to):
        result = super(MailMail, self)._get_unsubscribe_url(email_to)
        token = self.mailing_id._unsubscribe_token(self.res_id)
        return "%s&token=%s" % (result, token)
