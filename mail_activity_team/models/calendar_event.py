# Copyright 2019 Creu Blanca
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models, _


class CalendarEvent(models.Model):
    _inherit = 'calendar.event'

    def _get_default_team_id(self, user_id=None):
        if not user_id:
            user_id = self.env.uid
        domain = [('member_ids', 'in', [user_id])]
        res_model = self.env.context.get('default_res_model')
        if res_model:
            model = self.env['ir.model'].search(
                [('model', '=', res_model)], limit=1)
            domain.extend(['|', ('res_model_ids', '=', False),
                           ('res_model_ids', 'in', model.ids)])
        return self.env['mail.activity.team'].search(domain, limit=1)

    privacy = fields.Selection(selection_add=[
        ('team', 'Only team'),
    ])
    team_id = fields.Many2one(
        comodel_name='mail.activity.team',
        default=lambda s: s._get_default_team_id(),
    )

    def _get_read_fields(self, fields):
        expected_fields = ['privacy', 'team_id']
        extra_fields = []
        fixed_fields = [
            'id', 'allday', 'start', 'stop', 'display_start', 'display_stop',
            'duration', 'user_id', 'state', 'interval', 'count',
            'recurrent_id_date', 'rrule'
        ]
        recurrent_fields = self._get_recurrent_fields()
        public_fields = list(set(
            recurrent_fields + fixed_fields))
        if not fields:
            fields = list(self._fields)
        for field in expected_fields:
            if field not in fields:
                fields.append(field)
                extra_fields.append(field)
        return fields, extra_fields, public_fields

    @api.multi
    def read(self, fields=None, load='_classic_read'):
        # This function manages which fields a user can read based on the
        # team it belongs.

        fields, extra_fields, public_fields = self._get_read_fields(fields)
        result = super().read(fields, load)
        for r in result:
            if r['team_id'] and r['privacy'] == 'team':
                team_id = r['team_id']
                if isinstance(team_id, tuple):
                    team_id = team_id[0]
                team = self.env['mail.activity.team'].browse(team_id)
                users = team.member_ids
                if self.env.user not in users:
                    for f in r:
                        if f not in public_fields:
                            if isinstance(r[f], list):
                                r[f] = []
                            else:
                                r[f] = False
                        if f == 'name':
                            r[f] = _('Busy')
            for f in extra_fields:
                if f in r:
                    del r[f]
        return result
