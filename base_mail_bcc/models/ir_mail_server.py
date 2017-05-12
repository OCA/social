# -*- coding: utf-8 -*-
# © 2014-2017 Thomas Rehn (initOS GmbH)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from email.Utils import COMMASPACE

from openerp import models, api


class IrMailServer(models.Model):
    _inherit = "ir.mail_server"

    @api.model
    def send_email(self, message, mail_server_id=None, smtp_server=None,
                   smtp_port=None, smtp_user=None, smtp_password=None,
                   smtp_encryption=None, smtp_debug=False):
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

        return super(IrMailServer, self).send_email(
            message, mail_server_id=mail_server_id, smtp_server=smtp_server,
            smtp_port=smtp_port, smtp_user=smtp_user,
            smtp_password=smtp_password, smtp_encryption=smtp_encryption,
            smtp_debug=smtp_debug
        )
