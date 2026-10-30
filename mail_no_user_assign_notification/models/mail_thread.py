# Copyright 2024 Tecnativa - Víctor Martínez
# License AGPL-3 - See http://www.gnu.org/licenses/agpl-3.0.html

from odoo import models


class MailThread(models.AbstractModel):
    _inherit = "mail.thread"

    def _message_auto_subscribe_followers(self, updated_values, default_subtype_ids):
        """Remove user_id from updated_values if this model has been set.
        This will prevent the user from auto subscrube to records on creation and/or
        assignment."""
        if updated_values.get("user_id"):
            icp = self.sudo().env["ir.config_parameter"]
            models_to_skip = icp.get_param(
                "mail_no_user_assign_notification.models", ""
            )
            models_to_skip = [x.strip() for x in models_to_skip.split(",")]
            if self._name in models_to_skip:
                updated_values.pop("user_id")
        return super()._message_auto_subscribe_followers(
            updated_values=updated_values, default_subtype_ids=default_subtype_ids
        )
