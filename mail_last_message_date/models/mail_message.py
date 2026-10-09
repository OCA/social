# Copyright 2026 Quartile (https://www.quartile.co)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import api, models


class MailMessage(models.Model):
    _inherit = "mail.message"

    def _update_last_message_date(self):
        for message in self:
            if not (message.model and message.res_id):
                continue
            record = self.env[message.model].browse(message.res_id)
            if (
                "last_message_date" not in record._fields
                or not record._should_track_message(message)
            ):
                continue
            record.sudo().write({"last_message_date": message.date})

    @api.model_create_multi
    def create(self, vals_list):
        messages = super().create(vals_list)
        messages._update_last_message_date()
        return messages
