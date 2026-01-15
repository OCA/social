# Copyright 2026 Quartile (https://www.quartile.co)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from datetime import date, datetime, time

from odoo import _, fields, models
from odoo.exceptions import AccessError, UserError


class MailThread(models.AbstractModel):
    _inherit = "mail.thread"

    last_message_date = fields.Datetime(
        compute="_compute_last_message_date",
        search="_search_last_message_date",
        groups="base.group_user",
        help="Datetime of the latest message posted on the record.",
    )

    def _compute_last_message_date(self):
        dates = {}
        if self._origin.ids:
            self.env["mail.message"].flush(["model", "res_id", "message_type", "date"])
            self.env.cr.execute(
                """
                SELECT res_id, MAX(date) FROM mail_message
                WHERE model = %s AND res_id IN %s AND message_type = ANY(%s)
                GROUP BY res_id
                """,
                (
                    self._name,
                    tuple(self._origin.ids),
                    list(self._get_tracked_message_types()),
                ),
            )
            dates = dict(self.env.cr.fetchall())
        for record in self:
            record.last_message_date = dates.get(record._origin.id)

    def _search_last_message_date(self, operator, value):
        # The field's groups restrict reading it, not searching on it.
        if not self.env.su and not self.env.user.has_group("base.group_user"):
            raise AccessError(_("Only internal users can search on Last Message Date."))
        if operator not in ("=", "!=", "<", "<=", ">", ">="):
            raise UserError(
                _("Operator %s is not supported on Last Message Date.") % operator
            )
        self.env["mail.message"].flush(["model", "res_id", "message_type", "date"])
        query = """
            SELECT res_id FROM mail_message
            WHERE model = %s AND res_id IS NOT NULL AND message_type = ANY(%s)
            GROUP BY res_id
        """
        params = [self._name, list(self._get_tracked_message_types())]
        if isinstance(value, str) and len(value) == 10:
            value = fields.Date.to_date(value)
        if isinstance(value, date) and not isinstance(value, datetime):
            value = datetime.combine(
                value, time.max if operator in (">", "<=") else time.min
            )
        if not value and operator in ("=", "!="):
            in_operator = "inselect" if operator == "!=" else "not inselect"
            return [("id", in_operator, (query, params))]
        if operator == "!=":
            # As with a stored field, also match records without a tracked message
            query += " HAVING MAX(date) = %s"
            return [("id", "not inselect", (query, params + [value]))]
        query += " HAVING MAX(date) " + operator + " %s"
        return [("id", "inselect", (query, params + [value]))]

    def _get_tracked_message_types(self):
        """Return the message types that count; override to fix them per model."""
        param = (
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("mail_last_message_date.message_types")
        )
        valid_types = (
            self.env["mail.message"]._fields["message_type"].get_values(self.env)
        )
        message_types = [
            message_type
            for message_type in (value.strip() for value in (param or "").split(","))
            if message_type in valid_types
        ]
        # Without a valid type, no message counts
        return message_types
