# Copyright 2022 Camptocamp SA (https://www.camptocamp.com).
# @author Iván Todorovich <ivan.todorovich@camptocamp.com>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import models


class MailActivity(models.Model):
    _inherit = "mail.activity"

    def _check_activity_security_rule(self, level: str) -> bool:
        self.ensure_one()
        user = self.env.user
        if level == "team" and self.team_id and self.team_id in user.activity_team_ids:
            return True
        return super()._check_activity_security_rule(level)
