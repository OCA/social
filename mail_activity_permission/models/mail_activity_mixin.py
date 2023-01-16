# Copyright 2023 Hunki Enterprises BV
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from psycopg2.extensions import AsIs

from odoo import api, fields, models
from odoo.osv.expression import FALSE_DOMAIN


class MailActivityMixin(models.AbstractModel):
    _inherit = "mail.activity.mixin"

    activity_permission_ids = fields.One2many(
        comodel_name="mail.activity",
        compute="_compute_activity_permission_ids",
        search="_search_activity_permission_ids",
        groups="base.group_user",
        context={"active_test": False},
    )

    @api.depends("activity_ids")
    def _compute_activity_permission_ids(self):
        MailActivity = self.env["mail.activity"].with_context(active_test=False)
        type_ids = (
            self.env["mail.activity.type"]
            .search(
                [
                    ("perm_read", "=", True),
                    ("res_model_id.model", "in", (False, self._name)),
                ]
            )
            .ids
        )
        for this in self:
            this.activity_permission_ids = MailActivity.search(
                [
                    ("res_id", "=", this.id),
                    ("res_model", "=", self._name),
                    ("activity_type_id", "in", type_ids),
                ]
            )

    def _search_activity_permission_ids(self, op, val):
        if op != "in" or not val:
            return FALSE_DOMAIN
        self.env.cr.execute(
            "SELECT t.id FROM %(table)s t JOIN mail_activity a "
            "ON t.id=a.res_id AND a.res_model=%(model)s "
            "WHERE a.user_id=%(user_id)s AND a.id IN %(ids)s",
            {
                "table": AsIs(self._table),
                "model": self._name,
                "user_id": self.env.user.id,
                "ids": tuple(val),
            },
        )
        return [
            ("id", "in", tuple(_id for _id, in self.env.cr.fetchall())),
        ]
