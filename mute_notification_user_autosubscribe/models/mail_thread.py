# Copyright 2024 Manuel Regidor <manuel.regidor@sygel.es>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import models


class MailThread(models.AbstractModel):
    _inherit = "mail.thread"

    def _mute_user_autosubscribe_vals(self, vals, user):
        final_vals = vals
        field = self._fields.get("user_id")
        if field and user:
            model = self.env["ir.model"]._get(self._name)
            if self.env["user.autosubscribe.mute"].is_mute_user(model, user):
                subtype = self.env.ref("mute_notification_user_autosubscribe.muted")
                partner_id = user.partner_id.id
                final_vals = [p for p in vals if p[0] != partner_id]
                final_vals += [
                    (p[0], [subtype.id], p[2]) for p in vals if p[0] == partner_id
                ]
        return final_vals

    def _message_auto_subscribe_followers(self, updated_values, default_subtype_ids):
        vals = super()._message_auto_subscribe_followers(
            updated_values, default_subtype_ids
        )
        if vals:
            user_id = updated_values.get("user_id")
            if user_id:
                user = self.env["res.users"].browse(user_id)
                partner_id = user.partner_id.id
                # Do nothing in case the user is already subscribe.
                # It happes, for example, when it is the user_id who creates
                # the document
                if (
                    partner_id not in self.message_partner_ids.ids
                    and updated_values.get("user_id")
                ):
                    vals = self._mute_user_autosubscribe_vals(vals, user)
        return vals
