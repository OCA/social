# Copyright 2024 Manuel Regidor <manuel.regidor@sygel.es>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import models


class ResUsers(models.Model):
    _inherit = "res.users"

    def _is_muted(self, model):
        self.ensure_one()
        muted = False
        user_autosubscribe_mute = self.env["user.autosubscribe.mute"].search(
            [("model_id", "=", model.id)], limit=1
        )
        if user_autosubscribe_mute:
            groups = (
                ",".join(user_autosubscribe_mute.group_ids.get_external_id().values())
                or ""
            )
            if self.id in user_autosubscribe_mute.user_ids.ids or (
                groups and self.user_has_groups(groups)
            ):
                muted = True
        return muted
