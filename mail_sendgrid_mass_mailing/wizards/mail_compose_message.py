# -*- coding: utf-8 -*-
# Copyright 2016-2017 Compassion CH (http://www.compassion.ch)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, api


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
        all_mail_values = wizard.get_mail_values(res_ids)
        email_obj = self.env['mail.mail']
        emails = email_obj
        for res_id in res_ids:
            mail_values = all_mail_values[res_id]
            obj = self.env[wizard.model].browse(res_id)
            if wizard.model == 'res.partner':
                mail_values['recipient_ids'] = [(6, 0, obj.ids)]
            else:
                mail_values['email_to'] = obj.email
            emails += email_obj.create(mail_values)
        return emails
