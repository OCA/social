# Copyright 2025 Therp BV <https://thero.nl>.
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, models


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
