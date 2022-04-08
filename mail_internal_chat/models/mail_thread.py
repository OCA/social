# Copyright 2022 Camptocamp SA
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl)
from odoo import models


class MailThread(models.AbstractModel):

    _inherit = "mail.thread"

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
        new_recipients_data = recipients_data.copy()
        if kwargs.get("chat_window") and message.subtype_id.keep_chat_internal:
            rdata_partners = [
                notif
                for notif in recipients_data.get("partners")
                if notif.get("type") != "customer"
            ]
            new_recipients_data["partners"] = rdata_partners
        return super()._notify_record_by_email(
            message,
            new_recipients_data,
            msg_vals=msg_vals,
            model_description=model_description,
            mail_auto_delete=mail_auto_delete,
            check_existing=check_existing,
            force_send=force_send,
            send_after_commit=send_after_commit,
            **kwargs
        )
