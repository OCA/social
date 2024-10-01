# Copyright 2024 Tecnativa - Carlos Lopez
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).
from odoo import models


class MailThread(models.AbstractModel):
    _inherit = "mail.thread"

    def _notify_compute_recipients(self, message, msg_vals):
        recipients_data = super()._notify_compute_recipients(message, msg_vals)
        # only notify to explicit partners, remove others(followers).
        if self.env.context.get("message_forwarded_id"):
            current_partners_ids = message.partner_ids.ids
            new_recipeints = []
            for recipeint in recipients_data:
                if recipeint["id"] in current_partners_ids:
                    new_recipeints.append(recipeint)
            recipients_data = new_recipeints
        return recipients_data
