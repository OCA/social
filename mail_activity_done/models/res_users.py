# Copyright 2018-22 ForgeFlow <http://www.forgeflow.com>
# Copyright 2023 Tecnativa - Víctor Martínez
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html).
from collections import defaultdict

from odoo import api, fields, models


class ResUsers(models.Model):
    _inherit = "res.users"

    @api.model
    def systray_get_activities(self):
        # TODO: Simplify if Odoo allows to modify query
        res = super().systray_get_activities()
        # Convert list to dict
        user_activities = {}
        for item in res:
            user_activities[item["model"]] = item
        # Redo the method only with the archived records and subtract them.
        query = """SELECT array_agg(res_id) as res_ids, m.id, count(*),
                    CASE
                        WHEN %(today)s::date - act.date_deadline::date = 0 Then 'today'
                        WHEN %(today)s::date - act.date_deadline::date > 0 Then 'overdue'
                        WHEN %(today)s::date - act.date_deadline::date < 0 Then 'planned'
                    END AS states
                FROM mail_activity AS act
                JOIN ir_model AS m ON act.res_model_id = m.id
                WHERE user_id = %(user_id)s
                AND act.active = False
                GROUP BY m.id, states;
                """
        self.env.cr.execute(
            query,
            {
                "today": fields.Date.context_today(self),
                "user_id": self.env.uid,
            },
        )
        activity_data = self.env.cr.dictfetchall()
        records_by_state_by_model = defaultdict(
            lambda: {"today": set(), "overdue": set(), "planned": set(), "all": set()}
        )
        for data in activity_data:
            records_by_state_by_model[data["id"]][data["states"]] = set(data["res_ids"])
            records_by_state_by_model[data["id"]]["all"] = records_by_state_by_model[
                data["id"]
            ]["all"] | set(data["res_ids"])
        for model_id in records_by_state_by_model:
            model_dic = records_by_state_by_model[model_id]
            model = (
                self.env["ir.model"]
                .sudo()
                .browse(model_id)
                .with_prefetch(tuple(records_by_state_by_model.keys()))
            )
            allowed_records = self.env[model.model].search(
                [("id", "in", tuple(model_dic["all"]))]
            )
            if not allowed_records:
                continue
            today = len(model_dic["today"] & set(allowed_records.ids))
            overdue = len(model_dic["overdue"] & set(allowed_records.ids))
            # Decrease total
            user_activities[model.model]["total_count"] -= today + overdue
            user_activities[model.model]["today_count"] -= today
            user_activities[model.model]["overdue_count"] -= overdue
            user_activities[model.model]["planned_count"] -= len(
                model_dic["planned"] & set(allowed_records.ids)
            )
        return list(user_activities.values())
