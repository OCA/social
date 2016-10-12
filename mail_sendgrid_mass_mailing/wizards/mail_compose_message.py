# -*- encoding: utf-8 -*-
##############################################################################
#
#    Copyright (C) 2016 Compassion CH (http://www.compassion.ch)
#    Releasing children from poverty in Jesus' name
#    @author: Emanuel Cino <ecino@compassion.ch>
#
#    The licence is in the file __openerp__.py
#
##############################################################################

from openerp import models, api


class EmailComposeMessage(models.TransientModel):
    _inherit = 'mail.compose.message'

    @api.model
    def mass_mailing_sendgrid(self, res_ids, composer_values):
        """ Helper to generate a new e-mail given a template and objects.

        :param res_ids: ids of the resource objects
        :param composer_values: values for the composer wizard
        :return: browse records of created e-mails (one per resource object)
        """
        if not isinstance(res_ids, list):
            res_ids = [res_ids]
        wizard = self.create(composer_values)
        all_mail_values = wizard.get_mail_values(wizard, res_ids)
        email_obj = self.env['mail.mail']
        emails = email_obj
        for res_id in res_ids:
            mail_values = all_mail_values[res_id]
            emails += email_obj.create(mail_values)
        return emails
