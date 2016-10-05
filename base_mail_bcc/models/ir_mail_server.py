# -*- coding: utf-8 -*-
# © 2014-2016 Thomas Rehn (initOS GmbH)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from openerp import models, api
from email.Utils import COMMASPACE


class IrMailServer(models.Model):
    _inherit = "ir.mail_server"

    @api.model
    def send_email(self, message, **kwargs):
        """"Add global bcc email addresses"""

        # These are added here in send_email instead of build_email
        #  because build_email is independent from the database and does not
        #  have a cursor as parameter.

        ir_config_parameter = self.env["ir.config_parameter"]
        config_email_bcc = ir_config_parameter.\
            get_param("base_mail_bcc.bcc_to")

        if config_email_bcc:
            config_email_bcc = config_email_bcc.encode('ascii')
            existing_bcc = []
            if message['Bcc']:
                existing_bcc.append(message['Bcc'])
                del message['Bcc']
            message['Bcc'] = COMMASPACE.join(
                existing_bcc + config_email_bcc.split(',')
            )

        return super(IrMailServer, self).send_email(message, **kwargs)
