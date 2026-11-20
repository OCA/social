# Copyright 2024 Tecnativa - Carlos Lopez
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).
from odoo import models


class MailThread(models.AbstractModel):
    _inherit = "mail.thread"

    def _notify_get_recipients(self, message, msg_vals, **kwargs):
        recipients_data = super()._notify_get_recipients(message, msg_vals, **kwargs)
        # only notify to explicit partners, remove others(followers).
        if (
            self.env.context.get("message_forwarded_id")
            and self.env.context.get("forward_type", "") == "current_thread"
        ):
            current_partners_ids = message.partner_ids.ids
            new_recipeints = []
            for recipeint in recipients_data:
                if recipeint["id"] in current_partners_ids:
                    new_recipeints.append(recipeint)
            recipients_data = new_recipeints
        return recipients_data
