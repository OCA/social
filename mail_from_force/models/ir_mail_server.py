# -*- coding: utf-8 -*-
# © 2018 Daniel Reis
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).


from openerp import models, SUPERUSER_ID


class MailServer(models.Model):
    _inherit = 'ir.mail_server'

    def send_email(self, cr, uid, message, mail_server_id=None,
                   smtp_server=None, smtp_port=None,
                   smtp_user=None, smtp_password=None,
                   smtp_encryption=None, smtp_debug=False,
                   context=None):
        from_force = self.pool['ir.config_parameter'].get_param(
            cr, SUPERUSER_ID, 'mail.from.force', context=context)
        if from_force:
            message['Return-Path'] = from_force
            message['From'] = from_force
        return super(MailServer, self).send_email(
            cr, uid, message, mail_server_id,
            smtp_server, smtp_port,
            smtp_user, smtp_password,
            smtp_encryption, smtp_debug,
            context=context)
