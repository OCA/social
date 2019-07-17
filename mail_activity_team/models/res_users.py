# Copyright 2018 Eficent Business and IT Consulting Services, S.L.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
from odoo import api, models, fields, modules


class ResUsers(models.Model):
    _inherit = "res.users"

    activity_team_ids = fields.Many2many(
        comodel_name='mail.activity.team',
        relation='mail_activity_team_users_rel',
        string="Activity Teams",
    )

    @api.model
    def systray_get_activities(self):
        if not self._context.get('team_activities', False):
            return super().systray_get_activities()
        query = """SELECT m.id, count(*), act.res_model as model,
                                CASE
                                    WHEN %(today)s::date -
                                    act.date_deadline::date = 0 Then 'today'
                                    WHEN %(today)s::date -
                                    act.date_deadline::date > 0 Then 'overdue'
                                    WHEN %(today)s::date -
                                    act.date_deadline::date < 0 Then 'planned'
                                END AS states, act.user_id as user_id
                            FROM mail_activity AS act
                            JOIN ir_model AS m ON act.res_model_id = m.id
                            WHERE team_id in (
                                SELECT mail_activity_team_id
                                FROM mail_activity_team_users_rel
                                WHERE res_users_id = %(user_id)s
                            )
                            GROUP BY m.id, states, act.res_model, act.user_id;
                            """
        user = self.env.uid
        self.env.cr.execute(query, {
            'today': fields.Date.context_today(self),
            'user_id': user,
        })
        activity_data = self.env.cr.dictfetchall()
        model_ids = [a['id'] for a in activity_data]
        model_names = {n[0]: n[1] for n in
                       self.env['ir.model'].browse(model_ids).name_get()}

        user_activities = {}
        for activity in activity_data:
            if not user_activities.get(activity['model']):
                user_activities[activity['model']] = {
                    'name': model_names[activity['id']],
                    'model': activity['model'],
                    'type': 'activity',
                    'icon': modules.module.get_module_icon(
                        self.env[activity['model']]._original_module),
                    'total_count': 0, 'today_count': 0, 'overdue_count': 0,
                    'planned_count': 0,
                }
            user_activities[activity['model']][
                '%s_count' % activity['states']] += activity['count']
            if activity['states'] in ('today', 'overdue'):
                user_activities[activity['model']]['total_count'] += activity[
                    'count']
            if activity['user_id'] == user and \
                    activity['states'] in ('today', 'overdue'):
                user_activities[
                    activity['model']
                ]['total_count'] -= activity['count']

        return list(user_activities.values())
