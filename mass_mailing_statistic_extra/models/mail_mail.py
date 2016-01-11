# -*- coding: utf-8 -*-
# License AGPL-3: Antiun Ingenieria S.L. - Antonio Espinosa
# See README.rst file on addon root folder for more details

from openerp import models, api


class MailMail(models.Model):
    _inherit = 'mail.mail'

    @api.model
    def email_to_list_get(self, mail):
        email_list = []
        if mail.email_to:
            email_to = self.send_get_mail_to(mail)
            email_list += email_to
        for partner in mail.recipient_ids:
            email_to = self.send_get_mail_to(mail, partner=partner)
            email_list += email_to
        return email_list

    @api.model
    def create(self, vals):
        mail = super(MailMail, self).create(vals)
        if vals.get('statistics_ids'):
            email_list = self.email_to_list_get(mail)
            for stat in mail.statistics_ids:
                stat.write({
                    'email_from': mail.email_from,
                    'email_to': ';'.join(email_list),
                    'subject': mail.subject,
                })
        return mail
