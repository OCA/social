# Copyright 2022 ForgeFlow S.L. (https://forgeflow.com)
# License LGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import models
from odoo.tools.mail import email_normalize


class MailThread(models.AbstractModel):
    _inherit = "mail.thread"

    def _notify_thread_by_email(self, message, recipients_data, **kwargs):
        mail_server_model = self.env["ir.mail_server"].sudo()
        if message.email_from:
            mail_server_suggested = mail_server_model.search(
                [("smtp_user", "=", email_normalize(message.email_from))], limit=1
            )
            if (
                mail_server_suggested
                and message.mail_server_id.id != mail_server_suggested.id
            ):
                message.mail_server_id = mail_server_suggested.id
        return super()._notify_thread_by_email(
            message,
            recipients_data,
            **kwargs,
        )
