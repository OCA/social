# Copyright 2022 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import models


class MailThread(models.AbstractModel):
    _inherit = "mail.thread"

    def _notify_by_email_add_values(self, base_mail_values):
        """Add email_cc into mail.mail"""
        if self._context.get("email_cc", False):
            base_mail_values["email_cc"] = self._context.get("email_cc")
        return super()._notify_by_email_add_values(base_mail_values)

    def _notify_record_by_email(
        self,
        message,
        recipients_data,
        msg_vals=False,
        model_description=False,
        mail_auto_delete=True,
        check_existing=False,
        force_send=True,
        send_after_commit=True,
        **kwargs
    ):
        """Send context email cc from mail.compose to mail.mail"""
        if kwargs.get("email_cc"):
            self = self.with_context(email_cc=kwargs["email_cc"])
        return super()._notify_record_by_email(
            message,
            recipients_data,
            msg_vals,
            model_description,
            mail_auto_delete,
            check_existing,
            force_send,
            send_after_commit,
            **kwargs
        )
