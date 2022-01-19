# Copyright 2018-22 ForgeFlow <http://www.forgeflow.com>
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html).
from odoo import api, fields, models


class MailActivity(models.Model):

    _inherit = "mail.activity"

    active = fields.Boolean(default=True)
    done = fields.Boolean(default=False)
    state = fields.Selection(
        selection_add=[("done", "Done")],
        compute="_compute_state",
        search="_search_state",
    )
    date_done = fields.Date("Completed Date", index=True, readonly=True)

    @api.depends("date_deadline", "done")
    def _compute_state(self):
        res = super()._compute_state()
        for record in self.filtered(lambda activity: activity.done):
            record.state = "done"
        return res

    def _search_state(self, operator, operand):
        if not operand:
            # checking for is (not) set
            if operator == "=":
                # is not set - never happens actually so we create impossible domain
                return [("id", "=", False)]
            else:
                # is set - always - return empty domain
                return []
        else:
            # checking for value
            if operand == "done":
                if operator == "=":
                    return ["&", ("done", operator, True), ("active", "=", False)]
                else:
                    return ["&", ("done", operator, False), ("active", "=", True)]
            else:
                if operator == "=":
                    return [
                        "&",
                        (
                            "date_deadline",
                            {"today": "=", "overdue": "<", "planned": ">"}[operand],
                            fields.Date.today(),
                        ),
                        ("done", "=", False),
                    ]
                else:
                    return [
                        "|",
                        (
                            "date_deadline",
                            {"today": "!=", "overdue": ">=", "planned": "<="}[operand],
                            fields.Date.today(),
                        ),
                        ("done", "=", True),
                    ]


class MailActivityMixin(models.AbstractModel):

    _inherit = "mail.activity.mixin"
    activity_ids = fields.One2many(
        domain=lambda self: [("res_model", "=", self._name), ("active", "=", True)]
    )
