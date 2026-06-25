# Copyright 2022 Camptocamp (http://www.camptocamp.com).
# @author Iván Todorovich <ivan.todorovich@gmail.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class MailActivityType(models.Model):
    _inherit = "mail.activity.type"

    security_done = fields.Selection(
        selection=[("owner", "Creator"), ("user", "User"), ("all", "Anyone")],
        default="all",
        required=True,
    )
    security_edit = fields.Selection(
        selection=[("owner", "Creator"), ("user", "User"), ("all", "Anyone")],
        default="all",
        required=True,
    )
    security_cancel = fields.Selection(
        selection=[("owner", "Creator"), ("user", "User"), ("all", "Anyone")],
        default="all",
        required=True,
    )
    security_group_ids = fields.Many2many(
        comodel_name="res.groups",
        string="Security Management Groups",
        help="Members of these groups will be able to perform any operation "
        "without restrictions.",
    )

    def _get_activity_security_rules(self, operation: str):
        """Get the list of implicit levels for the given operation and level.

        Permissions levels are stacked, so if you set an "user" level, the "owner"
        rule will also be evaluated. However, if you set an "owner" level, the
        "user" rule won't be evaluated.
        """
        self.ensure_one()
        fname = f"security_{operation}"
        levels = list(dict(self._fields[fname].selection).keys())
        return levels[: levels.index(self[fname]) + 1]
