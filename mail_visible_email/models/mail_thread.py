# Copyright 2025 Therp BV <https://therp.nl>.
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, models

_VISIBLE_EMAIL_FIELDS = {"email_to", "email_cc", "email_bcc"}


class MailThread(models.AbstractModel):
    _inherit = "mail.thread"

    @api.model
    def _message_route_process(self, message, message_dict, routes):
        """Intercept message_dict to write 'to' and 'cc' to mail.message.

        Smtp does not deliver messages with a bcc header. If a message is
        received from a bcc address, this address will be in the raw
        Delivered-To header, which message_parse adds to the 'to' key
        of message_dict.
        """
        message_dict["email_to"] = message_dict.get("to", False)
        message_dict["email_cc"] = message_dict.get("cc", False)
        return super()._message_route_process(message, message_dict, routes)

    def _get_message_create_ignore_field_names(self):
        return super()._get_message_create_ignore_field_names() | _VISIBLE_EMAIL_FIELDS

    def _message_post_after_hook(self, message, msg_values):
        vals = {k: msg_values[k] for k in _VISIBLE_EMAIL_FIELDS if msg_values.get(k)}
        if vals:
            message.write(vals)
        return super()._message_post_after_hook(message, msg_values)
