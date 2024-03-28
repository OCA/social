# Copyright 2022 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl)

from odoo import _, models
from odoo.exceptions import AccessError


class MailActivity(models.Model):
    _inherit = "mail.activity"

    def action_done_schedule_next(self):
        group_intersect = False
        if set(self.env.user.groups_id) | set(
            self.activity_type_id.validator_group_ids
        ):
            group_intersect = True
        if (
            self.activity_type_id.category != "validation"
            or not self.activity_type_id.validator_group_ids
            or group_intersect
        ):
            return super().action_done_schedule_next()

        raise AccessError(
            _(
                "Only validators in groups {} are " "allowed to validate this activity."
            ).format(
                "\n".join(
                    g.display_name for g in self.activity_type_id.validator_group_ids
                )
            )
        )
