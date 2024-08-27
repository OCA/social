# Copyright 2024 Grupo Isonor
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from ast import literal_eval

from odoo import models


class MailThread(models.AbstractModel):
    _inherit = "mail.thread"

    def _notify_by_email_add_values(self, base_mail_values):
        """All messages are a response to the previous message.
        The entire conversation in the document is referenced."""
        res = super()._notify_by_email_add_values(base_mail_values)
        message_id = self.env["mail.message"].browse(res["mail_message_id"])
        if (
            not message_id
            or not message_id.model
            or not message_id.res_id
            or message_id.is_internal
        ):
            return res
        orig_id = self.env[message_id.model].browse(message_id.res_id)
        orig_non_internal_messages = orig_id.message_ids.filtered(
            lambda x: not x.is_internal and x.id != message_id.id
        )
        if len(orig_non_internal_messages) != 0:
            # Set the message as a reply to the previous message
            in_reply_to = orig_non_internal_messages[0].message_id
            header_in_reply_to = {
                "In-Reply-To": in_reply_to,
            }
            headers = res.get("headers")
            if headers:
                headers = literal_eval(headers)
                headers.update(header_in_reply_to)
                res["headers"] = repr(headers)
            else:
                res["headers"] = repr(header_in_reply_to)
        # Reconstruct the references (See RFC 5322, section 3.6.4)
        nref = orig_non_internal_messages.mapped("message_id")
        res["references"] = " ".join(reversed(nref))
        return res
