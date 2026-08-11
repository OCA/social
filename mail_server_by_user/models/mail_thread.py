# Copyright 2022 ForgeFlow S.L. (https://forgeflow.com)
# License LGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import models
from odoo.tools.mail import email_normalize


class MailThread(models.AbstractModel):
    _inherit = "mail.thread"

    def _notify_thread_by_email(
        self,
        message,
        recipients_data,
        msg_vals=False,
        mail_auto_delete=True,
        model_description=False,
        force_email_company=False,
        force_email_lang=False,
        resend_existing=False,
        force_send=True,
        send_after_commit=True,
        subtitles=None,
        **kwargs
    ):
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
        return super(MailThread, self)._notify_thread_by_email(
            message,
            recipients_data,
            msg_vals=msg_vals,
            mail_auto_delete=mail_auto_delete,
            model_description=model_description,
            force_email_company=force_email_company,
            force_email_lang=force_email_lang,
            resend_existing=resend_existing,
            force_send=force_send,
            send_after_commit=send_after_commit,
            subtitles=subtitles,
            **kwargs,
        )
