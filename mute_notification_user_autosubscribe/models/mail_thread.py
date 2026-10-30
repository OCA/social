# Copyright 2024 Manuel Regidor <manuel.regidor@sygel.es>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import models


class MailThread(models.AbstractModel):
    _inherit = "mail.thread"

    def _message_auto_subscribe_followers(self, updated_values, default_subtype_ids):
        user_id = updated_values.get("user_id")
        if user_id:
            model = self.env["ir.model"]._get(self._name)
            user = self.env["res.users"].browse(user_id)
            partner_id = user.partner_id.id
            # Do nothing in case the user is already subscribe.
            # It happes, for example, when it is the user_id who creates
            # the document
            if (
                partner_id not in self.message_partner_ids.ids
                and user
                and model
                and user._is_muted(model)
            ):
                default_subtype_ids = [
                    self.env.ref("mute_notification_user_autosubscribe.muted").id
                ]
        vals = super()._message_auto_subscribe_followers(
            updated_values, default_subtype_ids
        )
        return vals
