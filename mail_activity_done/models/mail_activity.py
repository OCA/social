# Copyright 2018-22 ForgeFlow <http://www.forgeflow.com>
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html).
from odoo import api, fields, models

delete_sentinel = object()


class MailActivity(models.Model):

    _inherit = "mail.activity"

    active = fields.Boolean(default=True)
    done = fields.Boolean(default=False)
    state = fields.Selection(
        selection_add=[("done", "Done")],
        compute="_compute_state",
        search="_search_state",
    )
    date_done = fields.Date("Completed Date", index="btree", readonly=True)

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

    def unlink(self):
        """Don't unlink if we're asked not to"""
        if self.env.context.get("mail_activity_done") != delete_sentinel:
            return super().unlink()

    def _action_done(self, feedback=False, attachment_ids=None):
        """Ask super not to delete the activity and set it to done"""
        self.write({"done": True, "active": False, "date_done": fields.Date.today()})
        return super(
            MailActivity,
            self.with_context(mail_activity_done=delete_sentinel),
        )._action_done(feedback=feedback, attachment_ids=attachment_ids)


class MailActivityMixin(models.AbstractModel):

    _inherit = "mail.activity.mixin"
    activity_ids = fields.One2many(
        domain=lambda self: [("res_model", "=", self._name), ("active", "=", True)]
    )

    def _read_progress_bar(self, domain, group_by, progress_bar):
        """
        Exclude completed activities from progress bar result.
        """
        execute_org = self._cr.execute

        def execute(query, params=None, log_exceptions=True):
            # Convert to string according to query type
            if hasattr(query, "as_string"):
                # psycopg2 SQL object
                try:
                    query_str = query.as_string(self._cr._cnx)
                except Exception:
                    query_str = str(query)
            elif isinstance(query, str):
                query_str = query
            else:
                # Composite SQL object - leave as is if no pattern
                query_str = str(query) if hasattr(query, "__str__") else query

            original_where = "WHERE res_model = '{}'".format(self._name)

            # Only modify if the pattern exists in the query
            if isinstance(query_str, str) and original_where in query_str:
                replace_where = (
                    "WHERE res_model = '{}' AND mail_activity.done = FALSE".format(
                        self._name
                    )
                )
                modified_query = query_str.replace(original_where, replace_where)
                return execute_org(
                    modified_query,
                    params=params,
                    log_exceptions=log_exceptions,
                )
            else:
                # Pass the original query without modification
                return execute_org(
                    query,
                    params=params,
                    log_exceptions=log_exceptions,
                )

        self._cr.execute = execute
        try:
            return super()._read_progress_bar(domain, group_by, progress_bar)
        finally:
            self._cr.execute = execute_org

    def _search_activity_state(self, operator, value):
        execute_org = self._cr.execute

        def execute(query, params=None, log_exceptions=True):
            # Convert to string according to query type
            if hasattr(query, "as_string"):
                # psycopg2 SQL object
                try:
                    query_str = query.as_string(self._cr._cnx)
                except Exception:
                    query_str = str(query)
            elif isinstance(query, str):
                query_str = query
            else:
                # Composite SQL object - leave as is if no pattern
                query_str = str(query) if hasattr(query, "__str__") else query

            pattern = "WHERE mail_activity.res_model = %(res_model_table)s"

            # Only modify if the pattern exists in the query
            if isinstance(query_str, str) and pattern in query_str:
                modified_query = query_str.replace(
                    pattern,
                    "WHERE mail_activity.res_model = %(res_model_table)s AND "
                    "mail_activity.done = FALSE",
                )
                return execute_org(
                    modified_query,
                    params=params,
                    log_exceptions=log_exceptions,
                )
            else:
                # Pass the original query without modification
                return execute_org(
                    query,
                    params=params,
                    log_exceptions=log_exceptions,
                )

        self._cr.execute = execute
        try:
            return super()._search_activity_state(operator, value)
        finally:
            self._cr.execute = execute_org
