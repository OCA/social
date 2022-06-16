# Copyright 2022 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

from odoo import models


class Message(models.Model):
    _inherit = "mail.message"

    def _get_notification_message_history(self):
        """Get the list of messages to include into an email notification history."""
        if not self.env[self.model]._mail_notification_include_history:
            return self.browse()
        domain = self._get_notification_message_history_domain()
        messages = self.env["mail.message"].search(domain, order="date desc")
        return messages - self

    def _get_notification_message_history_domain(self):
        """Return the domain for email and send message comments."""
        return [
            ("model", "=", self.model),
            ("res_id", "=", self.res_id),
            "|",
            "&",
            ("message_type", "=", "comment"),
            ("subtype_id", "=", self.env.ref("mail.mt_comment").id),
            ("message_type", "=", "email"),
        ]
