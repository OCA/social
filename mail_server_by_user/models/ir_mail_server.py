# Copyright 2022 ForgeFlow S.L. (https://forgeflow.com)
# License LGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
from odoo import api, models
from odoo.tools.mail import email_normalize


class IrMailServer(models.Model):

    _inherit = "ir.mail_server"

    @api.model
    def send_email(
        self,
        message,
        mail_server_id=None,
        smtp_server=None,
        smtp_port=None,
        smtp_user=None,
        smtp_password=None,
        smtp_encryption=None,
        smtp_debug=False,
        smtp_session=None,
    ):
        email_from = message["From"]
        if email_from:
            mail_server_suggested = self.search(
                [("smtp_user", "=", email_normalize(email_from))], limit=1
            )
            if mail_server_suggested:
                mail_server_id = mail_server_suggested.id
        return super().send_email(
            message,
            mail_server_id,
            smtp_server,
            smtp_port,
            smtp_user,
            smtp_password,
            smtp_encryption,
            smtp_debug,
            smtp_session,
        )
