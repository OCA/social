# Copyright 2018-22 ForgeFlow S.L.
# Copyright 2026 Dixmit
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
from collections import defaultdict

from odoo import api, fields, models, modules


class ResUsers(models.Model):
    _inherit = "res.users"

    activity_team_ids = fields.Many2many(
        comodel_name="mail.activity.team",
        relation="mail_activity_team_users_rel",
        string="Activity Teams",
    )

    @api.model
    def systray_get_activities(self):
        if not self.env.context.get("team_activities"):
            return super().systray_get_activities()
        activities = self.env["mail.activity"].search(
            [("team_id.member_ids", "=", self.env.uid)]
        )
        activities_by_record_by_model_name = defaultdict(
            lambda: defaultdict(lambda: self.env["mail.activity"])
        )
        for activity in activities:
            record = self.env[activity.res_model].browse(activity.res_id)
            activities_by_record_by_model_name[activity.res_model][record] += activity
        model_ids = list(
            {
                self.env["ir.model"]._get(name).id
                for name in activities_by_record_by_model_name.keys()
            }
        )
        user_activities = {}
        for (
            model_name,
            activities_by_record,
        ) in activities_by_record_by_model_name.items():
            domain = [("id", "in", list({r.id for r in activities_by_record.keys()}))]
            allowed_records = self.env[model_name].search(domain)
            if not allowed_records:
                continue
            module = self.env[model_name]._original_module
            icon = module and modules.module.get_module_icon(module)
            model = self.env["ir.model"]._get(model_name).with_prefetch(model_ids)
            user_activities[model_name] = {
                "id": model.id,
                "name": model.name,
                "model": model_name,
                "type": "activity",
                "icon": icon,
                "total_count": 0,
                "today_count": 0,
                "overdue_count": 0,
                "planned_count": 0,
                "actions": [
                    {
                        "icon": "fa-clock-o",
                        "name": "Summary",
                    }
                ],
            }
            for record, activities in activities_by_record.items():
                if record not in allowed_records:
                    continue
                for activity in activities:
                    user_activities[model_name]["%s_count" % activity.state] += 1
                    if (
                        activity.state in ("today", "overdue")
                        and activity.user_id != self.env.user
                    ):
                        user_activities[model_name]["total_count"] += 1
        return list(user_activities.values())
