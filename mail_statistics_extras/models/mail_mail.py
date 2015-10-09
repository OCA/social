# -*- coding: utf-8 -*-
# License AGPL-3: Antiun Ingenieria S.L. - Antonio Espinosa
# See README.rst file on addon root folder for more details

from openerp.osv import osv


class MailMail(osv.Model):
    _inherit = 'mail.mail'

    def email_to_list_get(self, cr, uid, mail, context=None):
        email_list = []
        if mail.email_to:
            email_to = self.send_get_mail_to(cr, uid, mail, context=context)
            email_list += email_to
        for partner in mail.recipient_ids:
            email_to = self.send_get_mail_to(cr, uid, mail, partner=partner,
                                             context=context)
            email_list += email_to
        return email_list

    def create(self, cr, uid, values, context=None):
        mail_id = super(MailMail, self).create(cr, uid, values,
                                               context=context)
        if values.get('statistics_ids'):
            mail = self.browse(cr, uid, mail_id, context=context)
            email_list = self.email_to_list_get(cr, uid, mail, context=context)
            for stat in mail.statistics_ids:
                stat.write({
                    'email_from': mail.email_from,
                    'email_to': ';'.join(email_list),
                    'subject': mail.subject,
                })
        return mail
