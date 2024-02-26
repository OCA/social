# Copyright 2018 Lorenzo Battistini - Agile Business Group
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import models


class MessageThread(models.AbstractModel):
    _inherit = "mail.thread"

    def _notify_record_by_email(
        self,
        message,
        recipients_data,
        msg_vals=None,
        model_description=False,
        mail_auto_delete=True,
        check_existing=False,
        force_send=True,
        send_after_commit=True,
        **kwargs,
    ):
        if self.env.user.company_id.force_mail_queue:
            force_send = False

        return super()._notify_record_by_email(
            message,
            recipients_data,
            msg_vals=msg_vals,
            model_description=model_description,
            mail_auto_delete=mail_auto_delete,
            check_existing=check_existing,
            force_send=force_send,
            send_after_commit=send_after_commit,
            **kwargs,
        )
