# Copyright 2025 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, models


class MailThread(models.AbstractModel):

    _inherit = "mail.thread"

    @api.model
    def message_route(
        self, message, message_dict, model=None, thread_id=None, custom_values=None
    ):
        email_to = message_dict.get("to", "")
        email_cc = message_dict.get("cc", "")
        email_bcc = message_dict.get("bcc", "")
        all_recipients = ",".join(filter(None, [email_to, email_cc, email_bcc]))
        if all_recipients:
            message_dict["recipients"] = all_recipients
            message_dict["to"] = all_recipients
        return super().message_route(
            message, message_dict, model, thread_id, custom_values
        )
