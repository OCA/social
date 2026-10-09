# Copyright 2022 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

from logging import getLogger

from odoo import models

_logger = getLogger(__name__)


class Message(models.Model):
    _inherit = "mail.message"

    def _get_notification_message_history(self):
        """Get the list of messages to include into an email notification history."""
        if not self.model:
            return self.browse()

        ir_model = self.env["ir.model"]._get(self.model)

        if not ir_model.include_mail_history:
            return self.browse()

        if hasattr(self.env[self.model], "_mail_notification_include_history"):
            _logger.warning(
                "The model %s uses the deprecated attribute "
                "_mail_notification_include_history. "
                "Please use the field include_mail_history on ir.model instead.",
                self.model,
            )

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
