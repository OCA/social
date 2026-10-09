# Copyright 2026 Quartile (https://www.quartile.co)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import fields, models


class MailLastMessageDateMixin(models.AbstractModel):
    _name = "mail.last.message.date.mixin"

    last_message_date = fields.Datetime(
        help="Datetime when a message was posted on the record.",
    )

    def _get_tracked_message_types(self):
        return []

    def _should_track_message(self, message):
        message_types = self._get_tracked_message_types()
        if not message_types:
            return True
        return message.message_type in message_types
